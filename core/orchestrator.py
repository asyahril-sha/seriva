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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from seriva.config.constants import DEFAULT_USER_CALL, ROLE_ID_NOVA, ROLES
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
from seriva.core.world_engine import WorldEngine
from seriva.roles.role_registry import get_role


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

    Menyatukan state, emosi, scene, world, role, dan LLMClient.
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

        # 3) (Nanti) command /nova, /role, dll. ditangani di layer bot dengan
        #    langsung mengubah active_role_id di UserState. Di sini kita hanya
        #    memastikan selalu ada role_state untuk role aktif.
        if user_state.active_role_id not in ROLES:
            # fallback aman: paksa ke Nova jika role tidak dikenal
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

        # 6) (Opsional) update intimacy pelan-pelan mengikuti level
        self.emotion_engine.maybe_increase_intimacy_by_level(role_state)

        # 7) Update scene (sementara simpel; Nova punya helper khusus)
        if role_state.role_id == ROLE_ID_NOVA:
            self._update_scene_for_nova(role_state, inp)
        else:
            # Default: kalau belum ada nilai, isi baseline halus
            scene = role_state.scene
            if not scene.location:
                scene.location = "ruang yang tenang"
            if not scene.posture:
                scene.posture = "duduk berhadapan"
            if not scene.activity:
                scene.activity = "ngobrol berdua"
            if not scene.ambience:
                scene.ambience = "suasana hangat, lampu tidak terlalu terang"
            if scene.time_of_day is None:
                scene.time_of_day = TimeOfDay.NIGHT
            if not scene.physical_distance:
                scene.physical_distance = "sebelahan"

        # 8) Bangun messages via role aktif & panggil LLM
        role_impl = get_role(role_state.role_id)
        messages = role_impl.build_messages(user_state, role_state, inp.text)

        reply_text = self.llm.generate_text(messages)

        # 9) Update waktu interaksi terakhir
        user_state.last_interaction_ts = inp.timestamp

        # 10) Simpan state
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
    # INTERNAL HELPERS: SCENE UNTUK NOVA
    # --------------------------------------------------

    def _update_scene_for_nova(self, role_state: RoleState, inp: OrchestratorInput) -> None:
        """Update SceneState Nova secara sangat sederhana."""

        scene = role_state.scene

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
        if any(word in t for word in ["peluk", "pelukan"]):
            self.scene_engine.gentle_hug(scene)
        elif any(word in t for word in ["sender", "nyender"]):
            self.scene_engine.lean_on_shoulder(scene)

    # --------------------------------------------------
    # COMMAND KHUSUS: FLASHBACK
    # --------------------------------------------------

    def _handle_flashback(
        self,
        user_state: UserState,
        world_state: WorldState,
        inp: OrchestratorInput,
    ) -> OrchestratorOutput:
        """Tangani /flashback: minta role aktif cerita satu momen indah."""

        role_state = user_state.get_or_create_role_state(user_state.active_role_id)

        # Instruksi generik ke role: ceritakan satu kenangan indah/khas.
        flashback_instruction = (
            "Mas meminta kamu untuk mengingat dan menceritakan satu momen indah "
            "atau momen yang sangat berkesan di antara kalian berdua. Ceritakan "
            "secara lembut dan romantis, tetap non-vulgar, fokus pada emosi dan "
            "gestur halus, seolah ini adalah flashback kenangan manis."
        )

        role_impl = get_role(role_state.role_id)
        messages = role_impl.build_messages(user_state, role_state, flashback_instruction)

        reply_text = self.llm.generate_text(messages)

        user_state.last_interaction_ts = inp.timestamp
        self._save_all(user_state, world_state)

        return OrchestratorOutput(
            reply_text=reply_text,
            active_role_id=user_state.active_role_id,
            session_mode=user_state.global_session_mode,
        )

    # --------------------------------------------------
    # COMMAND KHUSUS: PROVIDER (/nego, /deal, /mulai)
    # --------------------------------------------------

    def _handle_provider_commands(
        self,
        user_state: UserState,
        world_state: WorldState,
        inp: OrchestratorInput,
    ) -> OrchestratorOutput:
        role_state = user_state.get_or_create_role_state(user_state.active_role_id)

        # Hanya berlaku untuk role provider (terapis atau teman spesial)
        if not self._is_provider_role(role_state.role_id):
            reply = (
                "Perintah ini cuma berlaku untuk terapis pijat atau teman spesial, Mas. "
                "Pindah dulu ke role mereka pakai /role."
            )
            self._save_all(user_state, world_state)
            return OrchestratorOutput(
                reply_text=reply,
                active_role_id=user_state.active_role_id,
                session_mode=user_state.global_session_mode,
            )

        if inp.command_name == "nego":
            reply = self._handle_provider_nego(user_state, role_state, inp)
        elif inp.command_name == "deal":
            reply = self._handle_provider_deal(user_state, role_state, inp)
        else:  # "mulai"
            reply = self._handle_provider_mulai(user_state, role_state, inp)

        user_state.last_interaction_ts = inp.timestamp
        self._save_all(user_state, world_state)
        return OrchestratorOutput(
            reply_text=reply,
            active_role_id=user_state.active_role_id,
            session_mode=user_state.global_session_mode,
        )

    def _handle_provider_nego(self, user_state: UserState, role_state: RoleState, inp: OrchestratorInput) -> str:
        """Tangani /nego <harga> untuk role provider."""

        parts = inp.text.strip().split()
        if len(parts) < 2:
            return "Contoh pakai: /nego 250000"

        price_str = parts[1]
        try:
            price = int(price_str)
        except ValueError:
            return "Mas, tulis angkanya aja ya. Contoh: /nego 250000"

        session = role_state.session
        session.negotiated_price = price
        session.deal_confirmed = False

        role_info = ROLES.get(role_state.role_id)
        label_name = role_info.display_name if role_info else "aku"

        if role_info and role_info.category == "TERAPIS_PIJAT":
            return (
                f"{label_name} senyum pelan. \"Oke ya Mas, kita sepakat di Rp{price:,}. "
                "Kalau Mas setuju, ketik /deal biar aku siapin suasananya.\""
            )
        else:  # TEMAN_SPESIAL
            return (
                f"{label_name} mendekat sedikit. \"Untuk malam spesial ini di Rp{price:,}, "
                "aku bakal fokus bikin Mas senyaman mungkin. Kalau Mas fix, ketik /deal ya.\""
            )

    def _handle_provider_deal(self, user_state: UserState, role_state: RoleState, inp: OrchestratorInput) -> str:
        """Tangani /deal setelah /nego."""

        session = role_state.session
        role_info = ROLES.get(role_state.role_id)
        label_name = role_info.display_name if role_info else "aku"

        if session.negotiated_price is None:
            return "Belum ada harga yang disepakati, Mas. Nego dulu pakai /nego <angka>."

        session.deal_confirmed = True

        # Untuk teman spesial, set durasi imajiner (misal 6 jam = 360 menit)
        if role_info and role_info.category == "TEMAN_SPESIAL":
            session.declared_duration_minutes = 360
            return (
                f"✅ Booking dikonfirmasi, Mas. Malam ini {label_name} nemenin Mas penuh. "
                "Kalau Mas sudah siap, ketik /mulai biar kita mulai sesi pertama."
            )

        # Terapis pijat, tanpa durasi khusus
        return (
            f"✅ Deal ya Mas, Rp{session.negotiated_price:,}. "
            f"{label_name} siap siapin suasana. Kalau Mas mau mulai, ketik /mulai."
        )

    def _handle_provider_mulai(self, user_state: UserState, role_state: RoleState, inp: OrchestratorInput) -> str:
        """Tangani /mulai untuk memulai sesi provider."""

        session = role_state.session
        role_info = ROLES.get(role_state.role_id)
        label_name = role_info.display_name if role_info else "dia"

        if not session.deal_confirmed:
            return "Belum ada deal yang dikonfirmasi, Mas. Nego dulu, lalu /deal, baru /mulai."

        # Aktifkan sesi provider (tidak akan auto-berakhir, hanya /batal yang mengakhiri)
        session.active = True
        session.mode = SessionMode.PROVIDER_SESSION
        session.started_at_ts = inp.timestamp

        scene = role_state.scene

        if role_info and role_info.category == "TERAPIS_PIJAT":
            scene.location = "ruang pijat sederhana"
            scene.posture = "Mas berbaring tengkurap di kasur pijat"
            scene.activity = "sesi pijat relaksasi dimulai"
            scene.ambience = "lampu redup, aroma terapi lembut, suara musik pelan"
            scene.physical_distance = "sangat dekat"
            scene.last_touch = "pijatan lembut di punggung"

            return (
                f"{label_name} merapikan alas dan menyentuh punggung Mas pelan. "
                "\"Mulai ya Mas… tarik napas pelan, buang pelan. Biar semua tegangannya pelan-pelan hilang.\""
            )

        # TEMAN_SPESIAL (Davina / Sallsa)
        scene.location = "kamar hotel yang tenang"
        scene.posture = "duduk bersebelahan di tepi ranjang"
        scene.activity = "memulai malam khusus berdua"
        scene.ambience = "lampu hangat redup, city lights terlihat dari jendela"
        scene.physical_distance = "sangat dekat"
        scene.last_touch = "genggam tangan hangat"

        return (
            f"{label_name} duduk rapat di samping Mas, jemarinya menggenggam tangan Mas hangat. "
            "\"Malam ini kita pelan-pelan aja ya, Mas… ceritain apa pun yang lagi Mas rasain, "
            "biar aku yang nemenin sampai hati Mas lebih ringan.\""
        )
