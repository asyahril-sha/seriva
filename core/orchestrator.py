"""Main orchestrator for SERIVA.

Tugas utama Orchestrator:
- Terima pesan dari user (text) + konteks (user_id, timestamp, dsb.).
- Load atau inisialisasi UserState (per user) dari storage.
- Tentukan role aktif (untuk saat ini fokus ke Nova dulu).
- Analisis kasar intent user (sayang, kangen, marah, dsb.).
- Update emosi (EmotionEngine), scene (SceneEngine), dan world (WorldEngine).
- Bangun prompt via Role implementation (NovaRole) dan panggil LLM.
- Simpan kembali state dan kembalikan teks jawaban.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from seriva.config.constants import DEFAULT_USER_CALL, ROLE_ID_NOVA
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

    Untuk saat ini fokus Nova sebagai role utama. Nanti diperluas ke
    role lain lewat role_registry.
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

        # 1) Command khusus: END/BATAL mematikan sesi khusus
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

        # 2) (Nanti) command /nova, /role, dll. Untuk sekarang, pastikan Nova.
        if user_state.active_role_id != ROLE_ID_NOVA:
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

        # 6) Update scene (sementara simpel; nanti bisa dipintarkan)
        self._update_scene_for_nova(role_state, inp)

        # 7) Bangun messages via role aktif (Nova) & panggil LLM
        role_impl = get_role(role_state.role_id)
        messages = role_impl.build_messages(user_state, role_state, inp.text)

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

