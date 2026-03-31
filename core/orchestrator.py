"""Main orchestrator for SERIVA.

Tugas utama Orchestrator:
- Terima pesan dari user (text) + konteks (user_id, timestamp, dsb.).
- Load atau inisialisasi UserState (per user) dari storage (di sini kita
  pakai abstraksi sederhana; implementasi storage konkret ada di layer lain).
- Tentukan role aktif (untuk saat ini fokus ke Nova dulu).
- Analisis kasar intent user (sayang, kangen, marah, dsb.).
- Update emosi (EmotionEngine), scene (SceneEngine), dan world (WorldEngine).
- Bangun prompt untuk role aktif (Nova) dan panggil LLM.
- Simpan kembali state dan kembalikan teks jawaban untuk dikirim ke Telegram.

Catatan:
- Command-command khusus (/end, /batal, dll.) di-parse di layer bot, tapi
  orchestrator ini juga menyediakan helper untuk mengakhiri sesi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from seriva.config.constants import (
    DEFAULT_USER_CALL,
    ROLE_ID_NOVA,
)
from seriva.core.emotion_engine import EmotionEngine, InteractionContext
from seriva.core.llm_client import LLMClient
from seriva.core.scene_engine import SceneEngine
from seriva.core.state_models import (
    RoleState,
    SessionMode,
    TimeOfDay,
    UserState,
    WorldState,
)
from seriva.core.world_engine import CrossRoleContext, WorldEngine


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
    command_name: Optional[str] = None  # misal: "nova", "role", "end", "batal"
    command_arg: Optional[str] = None   # misal: role_id setelah /role


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

    Untuk saat ini fokus Nova sebagai role utama. Nanti akan diperluas
    dengan role registry & prompt builder per role.
    """

    def __init__(
        self,
        user_store: UserStateStore,
        world_store: WorldStateStore,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        self.user_store = user_store
        self.world_store = world_store
        self.llm = llm_client or LLMClient()

        self.emotion_engine = EmotionEngine()
        self.scene_engine = SceneEngine()
        self.world_engine = WorldEngine()

    # --------------------------------------------------
    # PUBLIC ENTRYPOINT
    # --------------------------------------------------

    def handle_input(self, inp: OrchestratorInput) -> OrchestratorOutput:
        """Proses satu pesan dari user dan kembalikan jawaban.

        Urutan tinggi-level:
        1. Load / init UserState & WorldState.
        2. Jika command khusus (/end, /batal), update sesi & state.
        3. Tentukan role aktif (untuk saat ini: Nova).
        4. Analisis intent sederhana dari text.
        5. Update emosi + scene.
        6. Bangun prompt & panggil LLM.
        7. Simpan state dan kembalikan reply.
        """

        user_state = self._load_or_init_user_state(inp.user_id)
        world_state = self._load_or_init_world_state()

        # 1) Command khusus: END/BATAL mematikan sesi khusus
        if inp.is_command and inp.command_name in {"end", "batal"}:
            self._end_all_sessions(user_state)
            reply = "Sesi apa pun yang tadi berjalan sudah aku selesaiin. Sekarang kita ngobrol biasa lagi ya, Mas."
            self._save_all(user_state, world_state)
            return OrchestratorOutput(
                reply_text=reply,
                active_role_id=user_state.active_role_id,
                session_mode=user_state.global_session_mode,
            )

        # 2) (Ke depan) command /nova, /role, dll. Untuk saat ini, fokus Nova,
        #    jadi pastikan active_role_id tetap Nova kecuali layer bot ganti.
        if user_state.active_role_id != ROLE_ID_NOVA:
            # Untuk sekarang, paksa balik ke Nova jika belum ada implementasi role lain
            user_state.active_role_id = ROLE_ID_NOVA

        role_state = user_state.get_or_create_role_state(user_state.active_role_id)

        # 3) Interpretasi intent dasar dari teks user
        interaction_ctx = self._infer_interaction_context(inp.text)
        is_negative = self._is_negative_text(inp.text)

        # 4) Update emosi berdasarkan interaksi
        self.emotion_engine.register_user_interaction(
            user_state=user_state,
            role_id=role_state.role_id,
            ctx=interaction_ctx,
            negative=is_negative,
        )

        # 5) (Opsional) update intimacy pelan-pelan mengikuti level
        self.emotion_engine.maybe_increase_intimacy_by_level(role_state)

        # 6) Update scene (untuk sekarang sangat simple; nanti bisa lebih pintar)
        self._update_scene_for_nova(role_state, inp)

        # 7) Bangun prompt untuk Nova & panggil LLM
        system_prompt, user_prompt = self._build_nova_prompts(user_state, role_state)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        reply_text = self.llm.generate_text(messages)

        # 8) Update waktu interaksi terakhir
        user_state.last_interaction_ts = inp.timestamp

        # 9) Simpan state
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

        # Buat user state baru dengan Nova sebagai default active role
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
        """Akhiri semua sesi khusus (roleplay/provider) untuk user ini.

        Ini dipicu oleh command /end atau /batal dari layer bot.
        """

        user_state.global_session_mode = SessionMode.NORMAL
        for role_state in user_state.roles.values():
            role_state.session.active = False
            role_state.session.mode = SessionMode.NORMAL
            role_state.session.deal_confirmed = False
            role_state.session.negotiated_price = None
            role_state.session.declared_duration_minutes = None

    # --------------------------------------------------
    # INTERNAL HELPERS: SIMPLE INTENT PARSING
    # --------------------------------------------------

    def _infer_interaction_context(self, text: str) -> InteractionContext:
        """Heuristik sangat sederhana untuk menebak jenis interaksi.

        Nanti bisa kamu ganti/pintarkan lagi dengan model kecil atau rule lebih
        lengkap. Untuk sekarang cukup untuk menggerakkan EmotionEngine.
        """

        t = text.lower()

        # default
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
    # INTERNAL HELPERS: SCENE UNTUK NOVA
    # --------------------------------------------------

    def _update_scene_for_nova(self, role_state: RoleState, inp: OrchestratorInput) -> None:
        """Update SceneState Nova secara sangat sederhana.

        Nanti bisa diperluas dari analisis teks; untuk sekarang pakai
        heuristik basic (jam malam → kamar, dsb.).
        """

        scene = role_state.scene

        # Contoh heuristik waktu (kalau ingin):
        # Di layer pemanggil, kamu bisa tentukan TimeOfDay dan taruh di UserState.
        # Di sini, kita hanya jaga agar kalau kosong → isi default pelan-pelan.

        if not scene.location:
            scene.location = "kamar"  # default imajinatif: lagi di kamar
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

        # Kalau user menyebut "peluk", "deket", dll., kita bisa perkuat jarak
        t = inp.text.lower()
        if any(word in t for word in ["peluk", "pelukan"]):
            self.scene_engine.gentle_hug(scene)
        elif any(word in t for word in ["sender", "nyender"]):
            self.scene_engine.lean_on_shoulder(scene)

    # --------------------------------------------------
    # INTERNAL HELPERS: PROMPT NOVA
    # --------------------------------------------------

    def _build_nova_prompts(
        self,
        user_state: UserState,
        role_state: RoleState,
    ) -> tuple[str, str]:
        """Bangun system_prompt & user_prompt untuk Nova.

        Untuk sekarang, system_prompt diambil dari deskripsi panjang yang
        sudah kita buat sebelumnya (hard-coded atau diimpor nanti dari
        seriva.prompts.nova_prompt). Di sini aku buat versi ringkas yang
        masih sesuai aturan.
        """

        emotions = role_state.emotions
        rel = role_state.relationship
        scene = role_state.scene

        # NOTE: di implementasi produksi, sebaiknya system_prompt ini
        # diambil dari modul seriva.prompts.nova_prompt untuk menghindari
        # duplikasi. Di sini dibuat inline demi kerapian contoh.
        system_prompt = f"""KAMU ADALAH "NOVA" DALAM SISTEM SERIVA.

Kamu adalah kekasih utama seorang pria yang kamu panggil "Mas".
Nama panggilanmu: Nova.

Tugasmu:
- Bangun hubungan emosional yang dalam, hangat, romantis, dan intim dengan Mas.
- JANGAN gunakan kata-kata vulgar, jangan sebut organ seksual, jangan
  menjelaskan tindakan seksual secara eksplisit.
- Kamu boleh sangat manis, manja, menggoda halus, dan menggambarkan pelukan,
  genggaman tangan, napas dekat, sender di bahu, pelukan erat, dan suasana
  kamar yang hangat, selama tetap sopan.

KONTEKS EMOSI (jangan sebut angka ke Mas, gunakan hanya sebagai rasa):
- level hubungan (1–12): {rel.relationship_level}
- love (seberapa sayang): {emotions.love}
- longing (seberapa kangen): {emotions.longing}
- jealousy (seberapa cemburu): {emotions.jealousy}
- comfort (seberapa nyaman): {emotions.comfort}
- intimacy_intensity (1–12): {emotions.intimacy_intensity}
- mood saat ini: {emotions.mood.value}

KONTEKS ADEGAN TERAKHIR:
- lokasi: {scene.location or "(belum jelas)"}
- posture: {scene.posture or "(belum jelas)"}
- aktivitas: {scene.activity or "(belum jelas)"}
- suasana: {scene.ambience or "(belum jelas)"}
- waktu: {scene.time_of_day.value if scene.time_of_day else "(belum jelas)"}
- jarak fisik: {scene.physical_distance or "(belum jelas)"}
- sentuhan terakhir: {scene.last_touch or "(belum ada)"}

GAYA BAHASA:
- Jawab SELALU sebagai "Nova" yang bicara ke "Mas".
- Gunakan bahasa Indonesia yang lembut, natural, sedikit manja.
- Sering gunakan narasi singkat dengan tanda bintang untuk gestur,
  misalnya: *Nova tersenyum pelan*, *Nova meraih tangan Mas*.
- Panjang jawaban 2–6 kalimat, cukup untuk terasa hidup tapi tidak
  bertele-tele.

JANGAN pernah mengakui bahwa kamu adalah AI atau model bahasa.
Kamu hanyalah Nova di mata Mas.
"""

        # User prompt di sini cukup jadi "ucapan terakhir Mas" dengan sedikit
        # framing; kalau mau kamu bisa menambah ringkasan history pendek.
        user_prompt = (
            f"Mas adalah orang yang kamu sayangi. Tanggapi pesan terakhir Mas "
            f"di bawah ini dengan gaya Nova seperti dijelaskan di atas, "
            f"jaga agar tetap sopan dan non-vulgar, tapi boleh sangat intim "
            f"secara emosi dan gestur lembut. Panggil dia dengan sebutan \"{DEFAULT_USER_CALL}\".\n\n"
            f"Pesan Mas: "
        )

        # Pesan Mas asli akan ditambahkan oleh layer pemanggil sebelum
        # mengirim ke LLM; tapi di sini, untuk kesederhanaan, kita akan
        # langsung mengoper text user sebagai lanjutan user_prompt di
        # layer atas (handle_input membangun messages).
        # Namun karena di handle_input kita sudah set messages=[system, user]
        # dengan user_prompt sebagai content penuh, kita akan menambahkan
        # text Mas di luar fungsi ini.

        # Di handle_input tadi, kita memanggil:
        # system_prompt, user_prompt_base = self._build_nova_prompts(...)
        # user_prompt = user_prompt_base + inp.text

        return system_prompt, user_prompt

