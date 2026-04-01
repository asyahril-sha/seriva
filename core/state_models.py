"""State models for SERIVA.

Berisi semua struktur data utama:
- EmotionState: emosi per user-role
- SceneState: posisi & suasana adegan
- RelationshipState: level hubungan & intensitas intim
- RoleSessionState: status sesi dengan role (mode, aktif/tidak)
- UserState: gabungan semua role untuk satu user
- WorldState: drama global & event penting

Semua angka level hanya dipakai untuk logika internal, jangan bocor ke user
secara teknis (di-convert jadi gaya bahasa/gestur oleh role & prompt).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from config.constants import (
    MAX_DRAMA_LEVEL,
    MAX_INTIMACY_INTENSITY,
    MAX_RELATIONSHIP_LEVEL,
    MIN_DRAMA_LEVEL,
    MIN_INTIMACY_INTENSITY,
    MIN_RELATIONSHIP_LEVEL,
)


# ==============================
# ENUMS & SIMPLE TYPES
# ==============================


class Mood(str, Enum):
    """Mood keseluruhan role saat ini (dipakai untuk warna respon)."""

    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    PLAYFUL = "playful"
    ANNOYED = "annoyed"
    JEALOUS = "jealous"
    TIRED = "tired"
    TENDER = "tender"  # lembut, sayang


class SessionMode(str, Enum):
    """Mode sesi aktif dengan suatu role."""

    NORMAL = "normal"          # chat biasa
    ROLEPLAY = "roleplay"      # mode roleplay intim
    PROVIDER_SESSION = "provider_session"  # sesi layanan (terapis, teman spesial)


class TimeOfDay(str, Enum):
    """Perkiraan waktu (buat warna suasana)."""

    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    LATE_NIGHT = "late_night"


# ==============================
# EMOTION & RELATIONSHIP
# ==============================


@dataclass
class EmotionState:
    """Emosi per user-role.

    Semua nilai 0–100, tapi dipakai secara relatif saja.
    """

    love: int = 30            # seberapa sayang
    longing: int = 30         # seberapa kangen
    jealousy: int = 0         # seberapa cemburu
    comfort: int = 40         # seberapa nyaman
    mood: Mood = Mood.NEUTRAL

    # Intensitas intim non-vulgar (1–12, sejalan dengan relationship_level)
    intimacy_intensity: int = MIN_INTIMACY_INTENSITY

    def clamp(self) -> None:
        """Pastikan nilai tetap di dalam rentang yang wajar."""

        self.love = max(0, min(100, self.love))
        self.longing = max(0, min(100, self.longing))
        self.jealousy = max(0, min(100, self.jealousy))
        self.comfort = max(0, min(100, self.comfort))

        self.intimacy_intensity = max(
            MIN_INTIMACY_INTENSITY,
            min(MAX_INTIMACY_INTENSITY, self.intimacy_intensity),
        )


@dataclass
class RelationshipState:
    """Level hubungan per user-role.

    relationship_level: 1–12 (Stranger → Intimate)
    """

    relationship_level: int = MIN_RELATIONSHIP_LEVEL

    def clamp(self) -> None:
        self.relationship_level = max(
            MIN_RELATIONSHIP_LEVEL,
            min(MAX_RELATIONSHIP_LEVEL, self.relationship_level),
        )


# ==============================
# SCENE / ADEGAN
# ==============================


@dataclass
class SceneState:
    """Kondisi adegan terakhir antara user dan role.

    Semua field boleh None/"" kalau belum di-set, dan akan diisi pelan-pelan
    oleh scene_engine tergantung percakapan.
    """

    location: str = ""         # contoh: "kamar", "ruang tamu", "kafe", "mobil"
    posture: str = ""          # contoh: "duduk di sofa", "rebahan", "berdiri dekat jendela"
    activity: str = ""         # contoh: "nonton film", "ngobrol", "rebahan bareng"

    user_clothing: str = ""    # optional, boleh dipakai halus
    role_clothing: str = ""    # optional, gaya pakaian Nova/role

    ambience: str = ""         # contoh: "lampu redup", "hujan di luar", "musik pelan"
    time_of_day: Optional[TimeOfDay] = None

    physical_distance: str = ""  # contoh: "jauh", "sebelahan", "sangat dekat", "pelukan"
    last_touch: str = ""         # contoh: "genggam tangan", "peluk", "elus rambut"

    last_scene_update_ts: Optional[float] = None  # timestamp unix, opsional


# ==============================
# SESSION STATE (MODE & STATUS)
# ==============================


@dataclass
class RoleSessionState:
    """Status sesi aktif per user-role.

    Penting: sesi TIDAK pernah berakhir otomatis.
    - session_active hanya berubah jadi False kalau user mengirim command END
      (misal /end atau /batal, tergantung implementasi handler).
    """

    active: bool = False
    mode: SessionMode = SessionMode.NORMAL

    # Misalnya buat provider: menyimpan apakah sudah /deal, harga, dsb.
    deal_confirmed: bool = False
    negotiated_price: Optional[int] = None

    # Misalnya untuk sesi panjang (companion 6 jam, pijat), ini hanya info cerita.
    # Sistem TIDAK mengakhiri sesi otomatis walaupun durasi habis.
    declared_duration_minutes: Optional[int] = None

    # Timestamp mulai sesi (opsional, buat worker kalau perlu efek longing/drama).
    started_at_ts: Optional[float] = None


# ==============================
# PER-ROLE STATE (untuk satu user)
# ==============================


@dataclass
class RoleState:
    """State lengkap untuk satu role terhadap satu user."""

    role_id: str
    emotions: EmotionState = field(default_factory=EmotionState)
    relationship: RelationshipState = field(default_factory=RelationshipState)
    scene: SceneState = field(default_factory=SceneState)
    session: RoleSessionState = field(default_factory=RoleSessionState)

    # Riwayat chat singkat per role (ID pesan atau text pendek, detail di memory/message_history)
    last_message_snippets: List[str] = field(default_factory=list)

    def clamp(self) -> None:
        """Clamp semua sub-state ke rentang aman."""

        self.emotions.clamp()
        self.relationship.clamp()


# ==============================
# USER STATE (SEMUA ROLE)
# ==============================


@dataclass
class UserState:
    """State utama untuk satu user SERIVA (di luar world state global).

    - user_id: identitas unik user (bisa Telegram user_id sebagai string)
    - active_role_id: role mana yang sedang aktif sekarang (Nova, Davina, dsb.)
    - roles: peta role_id -> RoleState
    """

    user_id: str

    active_role_id: str = "nova"  # default selalu Nova

    # Mode global untuk user ini (misal sedang di mode roleplay Nova)
    global_session_mode: SessionMode = SessionMode.NORMAL

    # Semua role yang pernah disentuh user ini
    roles: Dict[str, RoleState] = field(default_factory=dict)

    # Terakhir kali user interaksi (timestamp, buat background worker)
    last_interaction_ts: Optional[float] = None

    def get_or_create_role_state(self, role_id: str) -> RoleState:
        """Ambil RoleState untuk role_id, buat baru jika belum ada."""

        if role_id not in self.roles:
            self.roles[role_id] = RoleState(role_id=role_id)
        return self.roles[role_id]

    def clamp_all(self) -> None:
        """Clamp semua role agar nilai emosi/relasi tetap di rentang aman."""

        for role_state in self.roles.values():
            role_state.clamp()


# ==============================
# WORLD STATE (GLOBAL)
# ==============================


@dataclass
class WorldEvent:
    """Event penting di dunia SERIVA (bisa dipakai untuk flashback global/drama)."""

    timestamp: float
    user_id: str
    role_id: str
    description: str  # deskripsi naratif, aman & non-vulgar


@dataclass
class WorldState:
    """State global di seluruh SERIVA.

    - drama_level: 0–100, seberapa panas dunia SERIVA secara umum
    - events: log pendek event besar (untuk analisis / flashback high-level)
    """

    drama_level: int = 0
    events: List[WorldEvent] = field(default_factory=list)

    def clamp(self) -> None:
        self.drama_level = max(MIN_DRAMA_LEVEL, min(MAX_DRAMA_LEVEL, self.drama_level))

    def add_event(self, event: WorldEvent) -> None:
        self.events.append(event)
        # Bisa diberi batas max panjang list jika perlu di masa depan

