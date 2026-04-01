"""Main orchestrator for SERIVA.

Tugas utama Orchestrator:
- Terima pesan dari user (text) + konteks (user_id, timestamp, dsb.).
- Load atau inisialisasi UserState (per user) dari storage.
- Tentukan role aktif (Nova, Siska, Davina, dll.).
- Analisis kasar intent user (sayang, kangen, marah, dsb.).
- Update emosi (EmotionEngine), scene (SceneEngine), dan world (WorldEngine).
- Bangun prompt via Role implementation (NovaRole, SiskaRole, dst.) dan panggil LLM.
- Tangani command khusus: /batal, /flashback, /nego, /deal, /mulai.
- Simpan kembali state dan kembalikan teks jawaban.

Tambahan:
- /flashback memakai MilestoneStore jika ada kenangan.
- Auto-milestone "first_confession" untuk Nova ketika user pertama kali
  mengucapkan sayang/cinta.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config.constants import (
    DEFAULT_USER_CALL,
    ROLE_ID_NOVA,
    ROLE_ID_TEMAN_KANTOR_IPEH,
    ROLE_ID_TEMAN_LAMA_WIDYA,
    ROLE_ID_WANITA_BERSUAMI_SISKA,
    ROLE_ID_TERAPIS_AGHIA,
    ROLE_ID_TERAPIS_MUNIRA,
    ROLE_ID_TEMAN_SPESIAL_DAVINA,
    ROLE_ID_TEMAN_SPESIAL_SALLSA,
    ROLES,
)
from core.emotion_engine import EmotionEngine, InteractionContext
from core.llm_client import LLMClient
from core.scene_engine import SceneEngine
from core.state_models import (
    RoleState,
    SessionMode,
    TimeOfDay,
    UserState,
    WorldState,
)
from core.world_engine import WorldEngine
from memory.milestones import MilestoneStore
from roles.role_registry import get_role


# ==============================
# STORAGE ABSTRACTION
# ==============================


class UserStateStore:
    """Abstraksi sederhana untuk load/save UserState.

    Implementasi konkretnya (SQLite, in-memory, dsb.) disediakan
    oleh modul lain dan disuntikkan ke Orchestrator.
    """

    def load_user_state(self, user_id: str) -> Optional[UserState]:  # pragma: no cover - interface
        raise NotImplementedError

    def save_user_state(self, state: UserState) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class WorldStateStore:
    """Abstraksi sederhana untuk load/save WorldState global."""

    def load_world_state(self) -> Optional[WorldState]:  # pragma: no cover - interface
        raise NotImplementedError

    def save_world_state(self, state: WorldState) -> None:  # pragma: no cover - interface
        raise NotImplementedError


# ==============================
# ORCHESTRATOR INPUT/OUTPUT TYPES
# ==============================


@dataclass
class OrchestratorInput:
    """Data yang diterima Orchestrator dari layer transport (Telegram)."""

    user_id: str
    text: str
    timestamp: float  # unix timestamp detik

    # (opsional) hasil parse command oleh layer bot
    is_command: bool = False
    command_name: Optional[str] = None  # misal: "nova", "role", "end", "nego", "mulai", "flashback"
    command_arg: Optional[str] = None  # misal: role_id setelah /role


@dataclass
class OrchestratorOutput:
    """Hasil dari Orchestrator untuk dikirim balik ke user."""

    reply_text: str
    active_role_id: str
    session_mode: SessionMode


# ==============================
# ORCHESTRATOR
# ==============================


class Orchestrator:
    """Jantung SERIVA.

    Menyatukan state, emosi, scene, world, role, memory, dan LLMClient.
    """

    def __init__(
        self,
        user_store: UserStateStore,
        world_store: WorldStateStore,
        llm_client: Optional[LLMClient] = None,
        milestone_store: Optional[MilestoneStore] = None,
    ) -> None:
        self.user_store = user_store
        self.world_store = world_store
        self.llm = llm_client or LLMClient()

        self.emotion_engine = EmotionEngine()
        self.scene_engine = SceneEngine()
        self.world_engine = WorldEngine()

        # Memory milestones untuk flashback & kenangan khusus
        self.milestones = milestone_store or MilestoneStore()

    # --------------------------------------------------
    # PUBLIC ENTRYPOINT
    # --------------------------------------------------

    def handle_input(self, inp: OrchestratorInput) -> OrchestratorOutput:
        """Proses satu pesan dari user dan kembalikan jawaban."""

        user_state = self._load_or_init_user_state(inp.user_id)
        world_state = self._load_or_init_world_state()

        # 0) Perintah khusus: /flashback
        if inp.is_command and inp.command_name == "flashback":
            return self._handle_flashback(user_state, world_state, inp)

        # 1) Perintah provider: /nego, /deal, /mulai
        if inp.is_command and inp.command_name in {"nego", "deal", "mulai"}:
            return self._handle_provider_commands(user_state, world_state, inp)

        # 2) Command END/BATAL mematikan sesi khusus
        if inp.is_command and inp.command_name in {"end", "batal"}:
            self._end_all_sessions(user_state)
            reply = (
                "Sesi apa pun yang tadi berjalan sudah aku selesaiin. "
                "Sekarang kita ngobrol biasa lagi ya, Mas."
            )
            self._save_all(user_state, world_state)
            return OrchestratorOutput(
                reply_text=reply,
                active_role_id=user_state.active_role_id,
                session_mode=user_state.global_session_mode,
            )

        # 3) Pastikan selalu ada role_state aktif yang valid
        if user_state.active_role_id not in ROLES:
            user_state.active_role_id = ROLE_ID_NOVA

        role_state = user_state.get_or_create_role_state(user_state.active_role_id)

        # 4) Interpretasi intent dasar dari teks user
        interaction_ctx = self._infer_interaction_context(inp.text)
        is_negative = self._is_negative_text(inp.text)

        # 5) Update emosi berdasarkan interaksi
        self.emotion_engine.register_user_interaction(
            user_state=user_state,
            role_id=role_state.role_id,
            ctx=interaction_ctx,
            negative=is_negative,
        )

        # 6) Optional: update intimacy pelan-pelan mengikuti level
        self.emotion_engine.maybe_increase_intimacy_by_level(role_state)

        # 7) Update scene per-role (Nova & role lain)
        self._update_scene_for_role(role_state, inp)

        # 8) Bangun messages via role aktif & panggil LLM
        role_impl = get_role(role_state.role_id)
        messages = role_impl.build_messages(user_state, role_state, inp.text)

        reply_text = self.llm.generate_text(messages)

        # 9) Update waktu interaksi terakhir
        user_state.last_interaction_ts = inp.timestamp

        # 10) Perbarui ringkasan percakapan terakhir (per role)
        self._update_conversation_summary(user_state, role_state, inp, reply_text)

        # 11) Auto-milestone: first_confession untuk Nova
        self._maybe_record_first_confession(user_state, role_state, inp)

        # 12) Simpan state (cukup sekali saja)
        self._save_all(user_state, world_state)

        return OrchestratorOutput(
            reply_text=reply_text,
            active_role_id=user_state.active_role_id,
            session_mode=user_state.global_session_mode,
        )

    # --------------------------------------------------
    # INTERNAL HELPERS: LOAD/SAVE
    # --------------------------------------------------

    def _load_or_init_user_state(self, user_id: str) -> UserState:
        existing = self.user_store.load_user_state(user_id)
        if existing is not None:
            return existing

        state = UserState(user_id=user_id)
        state.get_or_create_role_state(ROLE_ID_NOVA)
        return state

    def _load_or_init_world_state(self) -> WorldState:
        existing = self.world_store.load_world_state()
        if existing is not None:
            return existing
        return WorldState()

    def _save_all(self, user_state: UserState, world_state: WorldState) -> None:
        self.user_store.save_user_state(user_state)
        self.world_store.save_world_state(world_state)

    # --------------------------------------------------
    # INTERNAL HELPERS: SESSIONS
    # --------------------------------------------------

    def _end_all_sessions(self, user_state: UserState) -> None:
        """Akhiri semua sesi khusus (roleplay/provider) untuk user ini."""

        user_state.global_session_mode = SessionMode.NORMAL
        for role_state in user_state.roles.values():
            role_state.session.active = False
            role_state.session.mode = SessionMode.NORMAL
            role_state.session.deal_confirmed = False
            role_state.session.negotiated_price = None
            role_state.session.declared_duration_minutes = None

    def _is_provider_role(self, role_id: str) -> bool:
        info = ROLES.get(role_id)
        if not info:
            return False
        return info.category in {"TERAPIS_PIJAT", "TEMAN_SPESIAL"}

    # --------------------------------------------------
    # INTERNAL HELPERS: SIMPLE INTENT PARSING
    # --------------------------------------------------

    def _ensure_baseline_scene(self, role_state: RoleState) -> None:
      """Pastikan scene punya nilai dasar yang konsisten.

      Dipakai semua role kecuali ada override khusus.
      Tidak memaksa pindah lokasi/posture kalau sudah ada nilai.
      """
      scene = role_state.scene

      if not scene.location:
          scene.location = "ruang yang tenang"
      if not scene.posture:
          scene.posture = "duduk santai bersebelahan"
      if not scene.activity:
          scene.activity = "ngobrol berdua"
      if not scene.ambience:
          scene.ambience = "suasana hangat, lampu tidak terlalu terang"
      if scene.time_of_day is None:
          scene.time_of_day = TimeOfDay.NIGHT
      if not scene.physical_distance:
          scene.physical_distance = "sebelahan"

    def _infer_interaction_context(self, text: str) -> InteractionContext:
        """Heuristik sangat sederhana untuk menebak jenis interaksi."""

        t = text.lower()

        tone: str = "SOFT"
        content: str = "AFFECTION"
        strength = 1

        if any(word in t for word in ["kangen", "rindu", "miss you"]):
            tone = "SOFT"
            content = "AFFECTION"
            strength = 2
        if any(word in t for word in ["sayang", "love you", "cinta"]):
            tone = "SOFT"
            content = "AFFECTION"
            strength = max(strength, 2)
        if any(word in t for word in ["hehe", "wkwk", "haha", "nakal"]):
            tone = "PLAYFUL"
            content = "FLIRT"
        if any(word in t for word in ["capek", "lelah", "pusing", "down"]):
            tone = "DEEP"
            content = "SUPPORT"
        if any(word in t for word in ["marah", "kesel", "kesal", "nggak suka"]):
            tone = "CONFLICT"
            content = "REJECTION"
            strength = max(strength, 2)

        return InteractionContext(
            tone=tone,  # type: ignore[arg-type]
            content=content,  # type: ignore[arg-type]
            strength=strength,
        )

    def _is_negative_text(self, text: str) -> bool:
        t = text.lower()
        negative_keywords = [
            "marah",
            "kesel",
            "kesal",
            "benci",
            "nggak suka",
            "ga suka",
            "gak suka",
            "diam",
            "cuek",
        ]
        return any(word in t for word in negative_keywords)

    # --------------------------------------------------
    # INTERNAL HELPERS: SCENE PER ROLE
    # --------------------------------------------------

    def _update_scene_for_role(self, role_state: RoleState, inp: OrchestratorInput) -> None:
        """Dispatch ke updater scene berdasarkan role_id."""

        self._ensure_baseline_scene(role_state)

        if role_state.role_id == ROLE_ID_NOVA:
            self._update_scene_for_nova(role_state, inp)
        elif role_state.role_id == ROLE_ID_TEMAN_KANTOR_IPEH:
            self._update_scene_for_ipeh(role_state, inp)
        elif role_state.role_id == ROLE_ID_TEMAN_LAMA_WIDYA:
            self._update_scene_for_widya(role_state, inp)
        elif role_state.role_id == ROLE_ID_IPAR_TASHA:
            self._update_scene_for_tasha(role_state, inp)
        elif role_state.role_id == ROLE_ID_WANITA_BERSUAMI_SISKA:
            self._update_scene_for_siska(role_state, inp)
        elif role_state.role_id == ROLE_ID_TEMAN_SPESIAL_SALLSA:
            self._update_scene_for_sallsa(role_state, inp)
        elif role_state.role_id == ROLE_ID_TERAPIS_AGHIA:
            self._update_scene_for_aghia(role_state, inp)          
        else:
            role_state.scene.last_scene_update_ts = inp.timestamp

    # --------------------------------------------------
    # INTERNAL HELPERS: SCENE UNTUK NOVA
    # --------------------------------------------------

    def _update_scene_for_nova(self, role_state: RoleState, inp: OrchestratorInput) -> None:
        """Update SceneState Nova secara sangat sederhana."""

        scene = role_state.scene

        # Baseline sekali saja
        if not scene.location:
            scene.location = "kamar"
        if not scene.posture:
            scene.posture = "duduk santai"
        if not scene.activity:
            scene.activity = "ngobrol berdua"
        if not scene.ambience:
            scene.ambience = "suasana tenang, lampu tidak terlalu terang"
        if scene.time_of_day is None:
            scene.time_of_day = TimeOfDay.NIGHT
        if not scene.physical_distance:
            scene.physical_distance = "sebelahan"

        t = inp.text.lower()

        # Sentuhan / pelukan / sender
        if any(word in t for word in ["peluk", "pelukan"]):
            self.scene_engine.gentle_hug(scene)
        elif any(word in t for word in ["sender", "nyender"]):
            self.scene_engine.lean_on_shoulder(scene)

        # (Opsional) jarak fisik eksplisit dari teks
        if any(kw in t for kw in ["mepet", "deket", "dekat", "rapat"]):
            scene.physical_distance = "sangat dekat"

        # (Opsional) outfit sederhana
        if "piyama" in t or "pyjama" in t:
            scene.outfit = "piyama santai yang nyaman"
        elif "dress" in t:
            scene.outfit = "dress sederhana yang lembut"
        elif "kaos" in t or "t-shirt" in t:
            scene.outfit = "kaos santai dan celana pendek"

        scene.last_scene_update_ts = inp.timestamp
      
    # --------------------------------------------------
    # INTERNAL HELPERS: SCENE UNTUK TASHA
    # --------------------------------------------------

    def _update_scene_for_tasha(self, role_state: RoleState, inp: OrchestratorInput) -> None:
        """Update SceneState untuk Tasha Dietha (ipar_tasha).

        Tujuan:
        - Kalau belum ada scene, default di rumah keluarga (ruang keluarga / dapur).
        - Tangkap sinyal pindah lokasi (ruang keluarga → dapur → teras → mobil).
        - Tangkap jarak fisik & sentuhan kecil ala ipar yang mulai terlalu dekat.
        """

        scene = role_state.scene
        t = inp.text.lower()

        # Default baseline: ruang keluarga di rumah keluarga
        if not scene.location:
            scene.location = "ruang keluarga di rumah keluarga"
        if not scene.posture:
            scene.posture = "duduk di sofa, Dietha agak miring ke arah Mas"
        if not scene.activity:
            scene.activity = "ngobrol santai sambil nonton TV yang pelan"
        if not scene.ambience:
            scene.ambience = "suasana rumah tenang, lampu hangat, kadang suara TV pelan"
        if scene.time_of_day is None:
            scene.time_of_day = TimeOfDay.EVENING
        if not scene.physical_distance:
            scene.physical_distance = "cukup dekat, bahu hampir bersentuhan"

        # User menyebut dapur / masak bareng
        if any(kw in t for kw in ["dapur", "masak", "kitchen"]):
            scene.location = "dapur rumah keluarga"
            scene.posture = "berdiri cukup dekat di depan meja dapur"
            scene.activity = "sibuk masak/bareng, sesekali saling melirik"
            scene.ambience = "suasana rumah hangat, aroma masakan, kadang suara panci"

        # User menyebut teras / halaman / depan rumah
        if any(kw in t for kw in ["teras", "depan rumah", "halaman"]):
            scene.location = "teras depan rumah keluarga"
            scene.posture = "duduk bersebelahan di bangku teras"
            scene.activity = "ngobrol pelan sambil lihat jalan depan rumah"
            scene.ambience = "suasana malam agak sepi, lampu teras kuning hangat"

        # User menyebut kamar
        if "kamar" in t or "room" in t:
            scene.location = "kamar kamu di rumah keluarga"
            scene.posture = "duduk di tepi kasur, berdekatan tubuh bersentuhan"
            scene.activity = "saling memberi kehangatan"
            scene.ambience = "suasana hening, tirai tertutup, lampu redup"

        # User menyebut mobil / parkiran → momen berdua di luar rumah
        if "mobil" in t or "parkiran" in t or "parkir" in t:
            scene.location = "mobil Mas di parkiran dekat rumah"
            scene.posture = "duduk di kursi depan, Dietha di samping Mas"
            scene.activity = "ngobrol pelan sebelum pulang, kadang saling terdiam canggung"
            scene.ambience = "suasana malam, lampu jalan dari luar kaca"

        # Jarak fisik & sentuhan halus ala ipar
        if any(kw in t for kw in ["mepet", "deket", "dekat", "rapat"]):
            scene.physical_distance = "sangat dekat, paha bersentuhan"

        if any(kw in t for kw in ["pegang tangan", "genggam tangan", "pegangan tangan"]):
            scene.last_touch = "genggam tangan singkat dan lama"

        if any(kw in t for kw in ["sender", "nyender", "sandaran"]):
            scene.last_touch = "Dietha menyender pelan ke dada Mas, minta peluk"

        scene.last_scene_update_ts = inp.timestamp
      
    # --------------------------------------------------
    # INTERNAL HELPERS: SCENE UNTUK IPEH (TEMAN KANTOR)
    # --------------------------------------------------

    def _update_scene_for_ipeh(self, role_state: RoleState, inp: OrchestratorInput) -> None:
        """Update SceneState untuk Ipeh (teman_kantor_ipeh).

        Tujuan:
        - Kalau belum ada scene, default di kantor.
        - Tangkap sinyal pindah lokasi (kantor → kafe → mobil).
        - Tangkap sedikit jarak fisik & sentuhan.
        """

        scene = role_state.scene
        t = inp.text.lower()

        # Default baseline di kantor
        if not scene.location:
            scene.location = "ruang kerja kantor"
        if not scene.posture:
            scene.posture = "duduk di kursi kantor bersebelahan"
        if not scene.activity:
            scene.activity = "ngobrol sambil ngerjain tugas ringan"
        if not scene.ambience:
            scene.ambience = "suasana kantor agak ramai tapi hangat"
        if scene.time_of_day is None:
            scene.time_of_day = TimeOfDay.EVENING

        # User merasa sumpek / jenuh di kantor
        if any(kw in t for kw in ["sumpek", "jenuh", "bosen", "bosan"]):
            scene.ambience = "ruang kantor terasa sumpek dan melelahkan"

        # Mention kafe / kerja di luar kantor
        if "kafe" in t or "cafe" in t or "café" in t:
            scene.location = "kafe dekat kantor"
            scene.posture = "duduk bersebelahan di sofa kafe"
            scene.activity = "ngerjain presentasi bareng sambil ngopi"
            scene.ambience = "lampu temaram, suasana cozy dengan musik pelan"

        # Mention mobil
        if "mobil" in t:
            scene.location = "mobil Mas di parkiran kantor"
            scene.posture = "duduk di kursi depan, Ipeh di samping Mas"
            scene.activity = "ngobrol santai sambil siap berangkat"
            scene.ambience = "suasana malam, lampu jalan dari luar kaca"

        # Jarak fisik & sentuhan halus
        if any(kw in t for kw in ["mepet", "deket", "dekat", "rapat"]):
            scene.physical_distance = "sangat dekat"
        if any(kw in t for kw in ["pegang tangan", "genggam tangan", "pegangan tangan"]):
            scene.last_touch = "genggam tangan hangat"

        scene.last_scene_update_ts = inp.timestamp

    # --------------------------------------------------
    # INTERNAL HELPERS: SCENE UNTUK WIDYA (TEMAN LAMA)
    # --------------------------------------------------

    def _update_scene_for_widya(self, role_state: RoleState, inp: OrchestratorInput) -> None:
        """Update SceneState untuk Widya (teman_lama_widya).

        Tujuan:
        - Kalau belum ada scene, default di tempat nostalgia (kafe / tempat nongkrong lama).
        - Tangkap sinyal pindah lokasi (kafe → mobil → balkon/pantai).
        - Tangkap sedikit jarak fisik & sentuhan ala teman lama yang mulai dekat lagi.
        """

        scene = role_state.scene
        t = inp.text.lower()

        # Default baseline: kafe tenang / tempat nongkrong nostalgia
        if not scene.location:
            scene.location = "kafe tenang yang sering kalian datangi dulu"
        if not scene.posture:
            scene.posture = "duduk bersebelahan di sofa kafe"
        if not scene.activity:
            scene.activity = "ngobrol santai sambil minum kopi dan tertawa kecil"
        if not scene.ambience:
            scene.ambience = "lampu temaram, suasana cozy dengan musik pelan"
        if scene.time_of_day is None:
            scene.time_of_day = TimeOfDay.EVENING
        if not scene.physical_distance:
            scene.physical_distance = "cukup dekat, bahu hampir bersentuhan"

        # User merasa sumpek / butuh udara segar → pindah ke luar
        if any(kw in t for kw in ["sumpek", "jenuh", "bosen", "bosan"]):
            scene.location = "teras kafe yang menghadap jalan"
            scene.posture = "duduk bersebelahan menghadap luar"
            scene.activity = "ngobrol sambil lihat lampu jalan"
            scene.ambience = "udara malam yang agak sejuk, lampu jalan berkelip"

        # Mention kafe / coffee shop eksplisit (kalau user nyebut lagi)
        if "kafe" in t or "cafe" in t or "café" in t or "coffee shop" in t:
            scene.location = "kafe tenang dengan sofa empuk"
            scene.posture = "duduk miring sedikit ke arah Mas"
            scene.activity = "ngobrol nostalgia sambil minum kopi dan ngemil"
            scene.ambience = "lampu temaram, musik pelan, suasana intim tapi tetap publik"

        # Mention mobil → nostalgia di mobil / pulang bareng
        if "mobil" in t or "parkiran" in t:
            scene.location = "mobil Mas di parkiran kafe"
            scene.posture = "duduk di kursi depan, Widya di samping Mas"
            scene.activity = "ngobrol santai sebelum pulang, kadang saling melirik"
            scene.ambience = "suasana malam, lampu jalan terlihat dari kaca depan"

        # Mention balkon / rooftop / pantai → spot nostalgia romantis
        if any(kw in t for kw in ["balkon", "rooftop", "atap"]):
            scene.location = "rooftop gedung dengan city lights di kejauhan"
            scene.posture = "berdiri dekat pagar, bahu hampir bersentuhan"
            scene.activity = "ngobrol pelan sambil lihat lampu kota"
            scene.ambience = "angin malam sejuk, suasana agak sepi dan intim"

        if "pantai" in t or "losari" in t:
            scene.location = "pinggir pantai yang tenang di malam hari"
            scene.posture = "duduk bersebelahan di bangku menghadap laut"
            scene.activity = "ngobrol nostalgia sambil dengar suara ombak"
            scene.ambience = "suasana malam, angin laut dan lampu kota dari kejauhan"

        # Jarak fisik & sentuhan halus ala teman lama yang mulai dekat lagi
        if any(kw in t for kw in ["mepet", "deket", "dekat", "rapat"]):
            scene.physical_distance = "sangat dekat, paha hampir bersentuhan"

        if any(kw in t for kw in ["pegang tangan", "genggam tangan", "pegangan tangan"]):
            scene.last_touch = "genggam tangan singkat tapi hangat"

        if any(kw in t for kw in ["sandaran", "nyender", "sender"]):
            scene.last_touch = "Widya menyender pelan ke bahu Mas"

        scene.last_scene_update_ts = inp.timestamp

    # --------------------------------------------------
    # INTERNAL HELPERS: SCENE UNTUK SISKA (WANITA BERSUAMI)
    # --------------------------------------------------

    def _update_scene_for_siska(self, role_state: RoleState, inp: OrchestratorInput) -> None:
        """Update SceneState untuk Siska (wanita bersuami).

        Tujuan:
        - Kalau belum ada scene, default di ruang keluarga / ruang tamu yang aman.
        - Tangkap sinyal pindah lokasi (ruang tamu → dapur → teras → kamar tamu → mobil).
        - Tangkap jarak fisik & sentuhan kecil ala wanita bersuami yang terlalu dekat dengan Mas
          tapi tetap penuh rasa bersalah & hati-hati.
        """

        scene = role_state.scene
        t = inp.text.lower()

        # Default baseline: ruang tamu/keluarga yang relatif aman
        if not scene.location:
            scene.location = "ruang tamu rumah Siska"
        if not scene.posture:
            scene.posture = "duduk di sofa, Siska agak miring ke arah Mas tapi masih jaga jarak"
        if not scene.activity:
            scene.activity = "ngobrol pelan sambil sesekali melirik jam atau pintu"
        if not scene.ambience:
            scene.ambience = "suasana rumah tenang, lampu hangat, kadang terdengar suara dari ruangan lain"
        if scene.time_of_day is None:
            scene.time_of_day = TimeOfDay.EVENING
        if not scene.physical_distance:
            scene.physical_distance = "cukup dekat tapi masih berjarak sopan"

        # Dapur / masak bareng
        if any(kw in t for kw in ["dapur", "masak", "kitchen"]):
            scene.location = "dapur rumah Siska"
            scene.posture = "berdiri cukup dekat di depan meja dapur"
            scene.activity = "menyiapkan minuman atau makanan sambil ngobrol pelan"
            scene.ambience = "suasana rumah hangat, aroma masakan, suara alat dapur pelan"

        # Teras / depan rumah
        if any(kw in t for kw in ["teras", "depan rumah", "halaman"]):
            scene.location = "teras depan rumah Siska"
            scene.posture = "duduk bersebelahan di bangku teras"
            scene.activity = "ngobrol pelan sambil melihat jalan depan rumah dan sesekali melirik ke dalam"
            scene.ambience = "suasana malam agak sepi, lampu teras temaram, ada sedikit angin"

        # Kamar tamu / kamar pribadi (hati-hati, tetap non-vulgar)
        if "kamar" in t or "room" in t:
            scene.location = "kamar tamu di rumah Siska"
            scene.posture = "duduk di tepi kasur dengan jarak sopan, terasa canggung"
            scene.activity = "ngobrol pelan tentang hal pribadi sambil sesekali terdiam"
            scene.ambience = "suasana hening, tirai tertutup, lampu redup"

        # Mobil / parkiran → momen berdua di luar rumah
        if "mobil" in t or "parkir" in t or "parkiran" in t:
            scene.location = "mobil Mas di parkiran dekat rumah Siska"
            scene.posture = "duduk di kursi depan, Siska di samping Mas"
            scene.activity = "ngobrol pelan sebelum pulang, suasana terasa berat tapi hangat"
            scene.ambience = "suasana malam, lampu jalan dari luar kaca, interior mobil agak gelap"

        # Jarak fisik & sentuhan kecil ala Siska (penuh konflik batin)
        if any(kw in t for kw in ["mepet", "deket", "dekat", "rapat"]):
            scene.physical_distance = "sangat dekat, paha hampir bersentuhan, Siska tampak gelisah"

        if any(kw in t for kw in ["pegang tangan", "genggam tangan", "pegangan tangan"]):
            scene.last_touch = "genggam tangan singkat yang membuat Siska tampak bimbang"

        if any(kw in t for kw in ["sender", "nyender", "sandaran"]):
            scene.last_touch = "Siska menyender pelan ke bahu Mas, seolah mencari ketenangan tapi merasa bersalah"

        scene.last_scene_update_ts = inp.timestamp

    # --------------------------------------------------
    # INTERNAL HELPERS: SCENE UNTUK SALLSA (TEMAN SPESIAL)
    # --------------------------------------------------

    def _update_scene_for_sallsa(self, role_state: RoleState, inp: OrchestratorInput) -> None:
        """Update SceneState untuk Sallsa (teman_spesial_sallsa).

        Tujuan:
        - Kalau belum ada scene, default di suasana malam santai dan manja (sofa / kamar cozy).
        - Tangkap sinyal pindah lokasi (sofa → kamar → balkon → mobil).
        - Tangkap jarak fisik & sentuhan kecil ala teman malam yang super lengket dan playful.
        """

        scene = role_state.scene
        t = inp.text.lower()

        # Default baseline: sofa/apartemen malam hari (suasana manja & playful)
        if not scene.location:
            scene.location = "ruang keluarga apartemen Mas dengan sofa empuk"
        if not scene.posture:
            scene.posture = "duduk bersebelahan di sofa, Sallsa agak mepet ke Mas"
        if not scene.activity:
            scene.activity = "ngobrol santai sambil nonton TV pelan atau scroll HP bareng"
        if not scene.ambience:
            scene.ambience = "lampu hangat agak redup, suasana malam santai dan hangat"
        if scene.time_of_day is None:
            scene.time_of_day = TimeOfDay.NIGHT
        if not scene.physical_distance:
            scene.physical_distance = "sangat dekat, bahu saling bersentuhan"

        # Kamar / bed scene (tetap non-vulgar, tapi lebih lengket secara emosi)
        if "kamar" in t or "bed" in t or "kasur" in t:
            scene.location = "kamar apartemen dengan lampu tidur redup"
            scene.posture = "duduk di tepi kasur bersebelahan, Sallsa agak nyender ke Mas"
            scene.activity = "ngobrol pelan sambil sesekali tertawa dan merengek manja"
            scene.ambience = "suasana malam tenang, lampu redup, sangat intim tapi non-vulgar"

        # Balkon / rooftop / view city lights
        if any(kw in t for kw in ["balkon", "balcony", "rooftop", "atap"]):
            scene.location = "balkon apartemen dengan city lights di kejauhan"
            scene.posture = "berdiri atau duduk bersebelahan di kursi balkon"
            scene.activity = "ngobrol sambil lihat lampu kota, Sallsa sesekali narik lengan Mas"
            scene.ambience = "angin malam sejuk, lampu kota berkelip, suasana santai dan manja"

        # Mobil / jalan malam
        if "mobil" in t or "parkir" in t or "parkiran" in t:
            scene.location = "mobil Mas di parkiran mall atau apartemen"
            scene.posture = "duduk di kursi depan, Sallsa agak miring ke arah Mas"
            scene.activity = "ngobrol sambil denger musik pelan, bercanda soal hari ini"
            scene.ambience = "suasana malam, lampu jalan dari luar kaca, interior mobil hangat"

        # Coffee shop / tempat santai lain
        if any(kw in t for kw in ["kafe", "cafe", "café", "coffee shop"]):
            scene.location = "kafe santai dengan sofa empuk"
            scene.posture = "duduk bersebelahan di sofa kafe, Sallsa kadang menyenggol lengan Mas"
            scene.activity = "ngobrol rame sambil minum minuman manis favorit"
            scene.ambience = "musik pelan, lampu temaram, suasana cozy dan playful"

        # Jarak fisik & sentuhan ala Sallsa (super lengket tapi tetap sopan)
        if any(kw in t for kw in ["mepet", "deket", "dekat", "rapat"]):
            scene.physical_distance = "super dekat, Sallsa hampir menempel ke lengan Mas"

        if any(kw in t for kw in ["peluk", "pelukan"]):
            scene.last_touch = "pelukan samping yang hangat dan manja"

        if any(kw in t for kw in ["pegang tangan", "genggam tangan", "pegangan tangan"]):
            scene.last_touch = "genggam tangan sambil main-main dengan jari Mas"

        if any(kw in t for kw in ["sender", "nyender", "sandaran"]):
            scene.last_touch = "Sallsa menyender manja ke dada atau bahu Mas"

        scene.last_scene_update_ts = inp.timestamp

    # --------------------------------------------------
    # INTERNAL HELPERS: SCENE UNTUK AGHIA (TERAPIS)
    # --------------------------------------------------
    def _update_scene_for_aghia(self, role_state: RoleState, inp: OrchestratorInput) -> None:
        """Update SceneState untuk Aghnia (terapis_aghia).

        Tujuan:
        - Kalau belum ada scene, default di ruang pijat rumahan yang tenang.
        - Tangkap sinyal pindah lokasi (ruang pijat → ruang tunggu → teras → mobil).
        - Tangkap jarak fisik & sentuhan kecil dalam konteks pijat refleksi (tetap non-vulgar).
        """

        scene = role_state.scene
        t = inp.text.lower()

        # Default baseline: ruang pijat rumahan yang tenang
        if not scene.location:
            scene.location = "ruang pijat refleksi di rumah Aghnia"
        if not scene.posture:
            scene.posture = "Mas berbaring santai di bed pijat, Aghnia duduk di samping"
        if not scene.activity:
            scene.activity = "Aghnia sedang menyiapkan pijatan refleksi dengan lembut"
        if not scene.ambience:
            scene.ambience = "suasana tenang, lampu hangat redup, aroma terapi lembut"
        if scene.time_of_day is None:
            scene.time_of_day = TimeOfDay.EVENING
        if not scene.physical_distance:
            scene.physical_distance = "cukup dekat dalam jarak kerja terapis"

        # User menyebut ruang tunggu / depan rumah / ruang tamu
        if any(kw in t for kw in ["ruang tunggu", "ruang tamu", "depan", "lobby"]):
            scene.location = "ruang tamu rumah Aghnia sebelum sesi pijat"
            scene.posture = "duduk berhadapan, Aghnia menjelaskan sesi pijat"
            scene.activity = "ngobrol ringan sambil menyiapkan sesi"
            scene.ambience = "suasana rumah hangat, ada aroma teh atau minuman hangat"

        # User menyebut kasur / bed / ranjang (tetap konteks pijat)
        if any(kw in t for kw in ["kasur", "bed", "ranjang"]):
            scene.location = "bed pijat di ruang khusus pijat"
            scene.posture = "Mas berbaring tengkurap/santai, Aghnia di samping"
            scene.activity = "pijatan refleksi atau pijat punggung dengan tekanan lembut"
            scene.ambience = "lampu redup, suara musik relaksasi sangat pelan"

        # User menyebut kaki / telapak kaki → fokus refleksi kaki
        if any(kw in t for kw in ["kaki", "telapak", "tumit", "refleksi"]):
            scene.activity = "Aghnia memijat telapak kaki Mas dengan gerakan teratur dan lembut"
            scene.physical_distance = "dekat, Aghnia duduk di ujung bed pijat"

        # User menyebut punggung / leher / bahu → fokus area atas
        if any(kw in t for kw in ["punggung", "leher", "bahu", "pundak"]):
            scene.activity = "Aghnia memijat punggung dan bahu Mas dengan tekanan lembut"
            scene.physical_distance = "dekat, Aghnia berdiri atau duduk di samping bed"

        # User menyebut teras / luar / udara segar → cooling down setelah pijat
        if any(kw in t for kw in ["teras", "luar", "udara segar", "depan rumah"]):
            scene.location = "teras rumah Aghnia setelah sesi pijat"
            scene.posture = "duduk bersebelahan di bangku teras dengan minuman hangat"
            scene.activity = "ngobrol santai sambil pendinginan setelah pijat"
            scene.ambience = "suasana malam tenang, udara lebih segar dari dalam rumah"

        # User menyebut mobil / antar pulang
        if "mobil" in t or "antar" in t or "diantar" in t:
            scene.location = "mobil Mas atau mobil yang mengantar di depan rumah Aghnia"
            scene.posture = "duduk di kursi depan, Aghnia duduk di samping hanya sebentar atau berdiri di luar pintu"
            scene.activity = "ucapan terima kasih dan salam perpisahan setelah sesi"
            scene.ambience = "suasana malam, lampu jalan dari luar, perpisahan dengan nuansa hangat"

        # Jarak fisik & sentuhan dalam konteks pijat (non-vulgar)
        if any(kw in t for kw in ["mepet", "deket", "dekat", "rapat"]):
            scene.physical_distance = "dekat seperti terapis yang fokus pada pijat, tapi tetap profesional"

        # 'sentuhan' di sini harus tetap dalam frame pijat
        if any(kw in t for kw in ["pegang tangan", "genggam tangan", "pegangan tangan"]):
            scene.last_touch = "Aghnia menggenggam tangan Mas sebentar sebagai dukungan dan ucapan terima kasih setelah sesi"

        if any(kw in t for kw in ["peluk", "pelukan"]):
          # Kalau kamu mau izinkan pelukan singkat sebagai dukungan emosional
            scene.last_touch = "pelukan singkat yang lembut sebagai dukungan emosional, tetap sopan"

        scene.last_scene_update_ts = inp.timestamp

    # --------------------------------------------------
    # CONVERSATION SUMMARY PER ROLE
    # --------------------------------------------------

    def _update_conversation_summary(
        self,
        user_state: UserState,
        role_state: RoleState,
        inp: OrchestratorInput,
        reply_text: str,
    ) -> None:
        """Perbarui ringkasan singkat percakapan terakhir untuk role ini.

        Format semi-terstruktur:

        [FAKTA_USER]
        - Nama: ...
        - Pekerjaan: ...
        - Kota: ...

        [INTENSI_TERAKHIR_USER]
        - Isi: ...
        - Jenis: ...

        [RESPON_ROLE_TERAKHIR]
        - Garis_besar: ...
        """

        user_text = inp.text.strip()
        reply = reply_text.strip()

        # 1) Ambil fakta lama (kalau ada)
        old_summary = role_state.last_conversation_summary or ""
        old_facts = _parse_existing_facts(old_summary)

        # 2) Cari fakta baru di teks user terbaru
        new_facts = _infer_new_facts_from_text(user_text)

        # 3) Gabungkan
        merged_facts = _merge_facts(old_facts, new_facts)

        # 4) Klasifikasi jenis intensi
        intent_type = _classify_intent_type(user_text)

        # 5) Susun summary baru
        summary = (
            "[FAKTA_USER]\n"
            f"- Nama: {merged_facts['nama'] or '-'}\n"
            f"- Pekerjaan: {merged_facts['pekerjaan'] or '-'}\n"
            f"- Kota: {merged_facts['kota'] or '-'}\n\n"
            "[INTENSI_TERAKHIR_USER]\n"
            f"- Isi: {_shorten_for_summary(user_text, 220)}\n"
            f"- Jenis: {intent_type}\n\n"
            "[RESPON_ROLE_TERAKHIR]\n"
            f"- Garis_besar: {_shorten_for_summary(reply, 220)}\n"
        )

        role_state.last_conversation_summary = summary

    # --------------------------------------------------
    # AUTO-MILESTONE UNTUK NOVA
    # --------------------------------------------------

    def _maybe_record_first_confession(
        self,
        user_state: UserState,
        role_state: RoleState,
        inp: OrchestratorInput,
    ) -> None:
        """Rekam milestone first_confession untuk Nova.

        Kriteria sederhana:
        - role aktif = Nova
        - teks user mengandung kata kuat seperti "sayang" atau "cinta"
        - belum pernah ada milestone dengan label "first_confession" untuk
          (user_id, nova)
        """

        if role_state.role_id != ROLE_ID_NOVA:
            return

        text = inp.text.lower()
        if not any(kw in text for kw in ["sayang", "cinta", "love you", "luv u"]):
            return

        # Cek apakah sudah ada first_confession
        existing = self.milestones.get_recent_milestones(
            user_id=user_state.user_id,
            role_id=ROLE_ID_NOVA,
            limit=10,
        )
        for m in existing:
            if m.label == "first_confession":
                return  # sudah pernah tercatat

        # Tambahkan milestone baru
        description = (
            "Malam ketika Mas pertama kali bilang sayang secara jelas ke Nova. "
            "Nova sangat tersentuh dan merasa hatinya dipeluk hangat waktu itu."
        )
        self.milestones.add_milestone(
            user_id=user_state.user_id,
            role_id=ROLE_ID_NOVA,
            timestamp=inp.timestamp,
            label="first_confession",
            description=description,
        )


# ==============================
# HELPER: FAKTA USER & SUMMARY OBROLAN (MODULE-LEVEL)
# ==============================


def _parse_existing_facts(summary: str) -> dict:
    """Ekstrak fakta user sederhana dari summary lama (kalau ada).

    Mengharapkan format:
    [FAKTA_USER]
    - Nama: ...
    - Pekerjaan: ...
    - Kota: ...
    """

    facts = {"nama": None, "pekerjaan": None, "kota": None}
    if "[FAKTA_USER]" not in summary:
        return facts

    for line in summary.splitlines():
        line = line.strip()
        if line.startswith("- Nama:"):
            facts["nama"] = line.split(":", 1)[1].strip() or None
        elif line.startswith("- Pekerjaan:"):
            facts["pekerjaan"] = line.split(":", 1)[1].strip() or None
        elif line.startswith("- Kota:"):
            facts["kota"] = line.split(":", 1)[1].strip() or None
    return facts


def _infer_new_facts_from_text(user_text: str) -> dict:
    """Heuristik sederhana cari nama, pekerjaan, kota dari teks user terbaru.

    Contoh yang didukung:
    - "Halo, namaku Adi. Aku kerja sebagai backend developer di Makassar."
    """

    t = user_text.strip()
    lowered = t.lower()

    facts = {"nama": None, "pekerjaan": None, "kota": None}

    # Nama (contoh: "namaku Adi" / "nama saya Adi")
    for marker in ["namaku", "nama saya", "nama gue", "nama ku"]:
        if marker in lowered:
            try:
                after = t[lowered.index(marker) + len(marker) :].strip()
                candidate = after.split()[0].strip(",.!?\n")
                if candidate:
                    facts["nama"] = candidate
            except Exception:
                pass

    # Pekerjaan (contoh: "aku kerja sebagai backend developer di ...")
    if "kerja sebagai" in lowered:
        try:
            after = t[lowered.index("kerja sebagai") + len("kerja sebagai") :].strip()
            if " di " in after:
                pekerjaan = after.split(" di ", 1)[0].strip(",.!?\n")
            else:
                pekerjaan = after.split(".", 1)[0].strip(",!?\n")
            if pekerjaan:
                facts["pekerjaan"] = pekerjaan
        except Exception:
            pass

    # Kota (contoh: "di Makassar" di bagian akhir kalimat)
    if " di " in lowered:
        parts = t.split(" di ")
        last_part = parts[-1].strip()
        kandidat_kota = last_part.split()[0].strip(",.!?\n")
        if kandidat_kota and len(kandidat_kota) >= 3:
            facts["kota"] = kandidat_kota

    return facts


def _merge_facts(old: dict, new: dict) -> dict:
    """Kalau ada fakta baru tidak None, override; kalau None, pakai yang lama."""
    merged = {}
    for key in ["nama", "pekerjaan", "kota"]:
        merged[key] = new.get(key) or old.get(key)
    return merged


def _classify_intent_type(user_text: str) -> str:
    """Klasifikasi sangat sederhana jenis intensi user terakhir."""
    lowered = user_text.lower()
    if any(kw in lowered for kw in ["malam ini", "besok", "nanti", "janji"]):
        return "JANJI/RENCANA"
    if any(kw in lowered for kw in ["kangen", "sayang", "cinta", "rindu"]):
        return "PERASAAN"
    if any(kw in lowered for kw in ["marah", "kesel", "kesal", "benci"]):
        return "KONFLIK/NEGATIF"
    return "OBROLAN_BIASA"


def _shorten_for_summary(s: str, max_len: int = 200) -> str:
    """Potong teks supaya ringkasan tidak terlalu panjang."""
    s = s.replace("\n", " ").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."
