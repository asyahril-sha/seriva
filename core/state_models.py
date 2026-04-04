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
# BARU: INTIMACY & POSITION ENUMS
# ==============================

class IntimacyPhase(str, Enum):
    """Fase natural intimacy - semua role."""
    AWAL = "awal"           # masih canggung, jaga jarak
    DEKAT = "dekat"         # mulai nyaman, sentuhan tidak sengaja
    INTIM = "intim"         # pelukan, genggaman, napas dekat
    VULGAR = "vulgar"       # aktivitas seksual intens (level 10-12)
    AFTER = "after"         # setelah intim, suasana tenang/hangat


class SceneSequence(str, Enum):
    """Urutan scene yang harus diingat."""
    USER_DATANG = "user_datang"
    NGOBROL = "ngobrol"
    MENDEKAT = "mendekat"
    SENTUHAN_PERTAMA = "sentuhan_pertama"
    PELUKAN = "pelukan"
    CIUMAN = "ciuman"
    PETTING = "petting"
    SEX_MULAI = "sex_mulai"
    SEX_INTENS = "sex_intens"
    CLIMAX = "climax"
    AFTER_SEX = "after_sex"
    TIDUR = "tidur"
    PAGI_HARI = "pagi_hari"


class SexPosition(str, Enum):
    """Posisi seks yang mungkin terjadi."""
    MISSIONARY = "missionary"
    COWGIRL = "cowgirl"
    REVERSE_COWGIRL = "reverse_cowgirl"
    DOGGY = "doggystyle"
    SPOON = "spooning"
    SITTING = "sitting"
    STANDING = "standing"
    SIDE = "side"
    EDGE = "edge"
    PRONE = "prone"
    CHAIR = "chair"
    WALL = "wall"
    CAR = "car"


class Dominance(str, Enum):
    """Siapa yang dominan dalam adegan."""
    USER_DOMINANT = "user_dominant"
    ROLE_DOMINANT = "role_dominant"
    SWITCH = "switch"
    NEUTRAL = "neutral"


class IntimacyIntensity(str, Enum):
    """Tingkat intensitas adegan saat ini."""
    FOREPLAY = "foreplay"
    PETTING = "petting"
    ORAL_GIVING = "oral_giving"
    ORAL_RECEIVING = "oral_receiving"
    PENETRATION = "penetration"
    THRUSTING = "thrusting"
    CLIMAX = "climax"
    AFTER = "after"


# ==============================
# BARU: LOCATION & USER CONTEXT
# ==============================


@dataclass
class LocationContext:
    """Informasi lengkap tentang lokasi saat ini."""
    name: str
    type: str  # "private", "public", "semi_public"
    owner: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class UserContext:
    """Informasi tentang user (Mas) yang harus diingat role."""
    name: str = "Mas"
    preferred_name: Optional[str] = None
    job: Optional[str] = None
    city: Optional[str] = None
    has_apartment: bool = False
    apartment_note: Optional[str] = None


@dataclass
class IntimacyDetail:
    """Detail lengkap adegan intim saat ini."""
    position: Optional[SexPosition] = None
    dominance: Dominance = Dominance.NEUTRAL
    intensity: IntimacyIntensity = IntimacyIntensity.FOREPLAY
    last_action: str = ""
    last_pleasure: str = ""
    user_clothing_removed: List[str] = field(default_factory=list)
    role_clothing_removed: List[str] = field(default_factory=list)
    duration_minutes: int = 0
    
    def get_summary(self) -> str:
        if not self.position:
            return "Belum ada aktivitas intim yang intens."
        
        pos_name = {
            SexPosition.MISSIONARY: "misionaris (Mas di atas)",
            SexPosition.COWGIRL: "cowgirl (role di atas)",
            SexPosition.REVERSE_COWGIRL: "reverse cowgirl (role di atas membelakangi)",
            SexPosition.DOGGY: "doggy (dari belakang)",
            SexPosition.SPOON: "spooning (dari samping)",
            SexPosition.SITTING: "duduk berhadapan",
            SexPosition.STANDING: "berdiri",
            SexPosition.EDGE: "di tepi kasur/sofa",
            SexPosition.PRONE: "telungkup",
            SexPosition.CHAIR: "di kursi",
            SexPosition.WALL: "bersandar di tembok",
            SexPosition.CAR: "di mobil",
        }.get(self.position, self.position.value if self.position else "unknown")
        
        dom_name = {
            Dominance.USER_DOMINANT: "Mas yang lebih dominan",
            Dominance.ROLE_DOMINANT: "Role yang lebih dominan",
            Dominance.SWITCH: "kalian bergantian",
            Dominance.NEUTRAL: "sama-sama aktif",
        }.get(self.dominance, "netral")
        
        intensity_name = {
            IntimacyIntensity.FOREPLAY: "masih foreplay/pemanasan",
            IntimacyIntensity.PETTING: "sudah pegang-pegangan",
            IntimacyIntensity.ORAL_GIVING: "sedang memberikan oral",
            IntimacyIntensity.ORAL_RECEIVING: "sedang menerima oral",
            IntimacyIntensity.PENETRATION: "sedang penetrasi",
            IntimacyIntensity.THRUSTING: "sedang aktif bergerak",
            IntimacyIntensity.CLIMAX: "sudah/mau climax",
            IntimacyIntensity.AFTER: "sudah selesai, pendinginan",
        }.get(self.intensity, "sedang berlangsung")
        
        return f"""POSISI: {pos_name}
DOMINASI: {dom_name}
INTENSITAS: {intensity_name}
AKSI TERAKHIR: {self.last_action or "-"}
PERASAAN TERAKHIR: {self.last_pleasure or "-"}"""


@dataclass
class SceneTurn:
    """Satu adegan yang disimpan."""
    timestamp: float
    sequence: SceneSequence
    location: str
    physical_state: str
    user_action: str
    role_feeling: str


@dataclass
class ConversationTurn:
    """Satu putaran percakapan yang disimpan."""
    timestamp: float
    user_text: str
    role_response: str
    intimacy_phase: IntimacyPhase
    scene_sequence: SceneSequence
    key_event: Optional[str] = None
    user_emotion: Optional[str] = None

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

    Semua field boleh kosong kalau belum di-set.
    """

    location: str = ""          # contoh: "kamar", "ruang tamu", "kafe", "mobil"
    posture: str = ""           # contoh: "duduk di sofa", "rebahan", "berdiri dekat jendela"
    activity: str = ""          # contoh: "nonton film", "ngobrol", "rebahan bareng"

    user_clothing: str = ""     # optional, pakaian user (kalau mau dipakai halus)
    role_clothing: str = ""     # optional, pakaian role (bisa digabung ke outfit kalau mau)

    ambience: str = ""          # contoh: "lampu redup", "hujan di luar", "musik pelan"
    time_of_day: Optional[TimeOfDay] = None

    physical_distance: str = "" # contoh: "jauh", "sebelahan", "sangat dekat", "pelukan"
    last_touch: str = ""        # contoh: "genggam tangan", "peluk", "elus rambut"

    outfit: Optional[str] = None # ringkasan penampilan role saat ini (opsional)

    last_scene_update_ts: Optional[float] = None
    

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
    
    total_positive_interactions: int = 0

    # Riwayat chat singkat per role (ID pesan atau text pendek, detail di memory/message_history)
    last_message_snippets: List[str] = field(default_factory=list)
    last_conversation_summary: Optional[str] = None
    long_term_summary: Optional[str] = None  # kalau nanti kamu pakai

    # ========== BARU: Memory System ==========
    conversation_memory: List[ConversationTurn] = field(default_factory=list)
    scene_memory: List[SceneTurn] = field(default_factory=list)
    intimacy_phase: IntimacyPhase = IntimacyPhase.AWAL
    current_sequence: Optional[SceneSequence] = None
    
    # Hindari repetisi
    last_feeling: str = ""
    last_response_style: str = ""
    is_high_intimacy: bool = False
    
    # ========== BARU: Location & User Context ==========
    current_location: Optional[LocationContext] = None
    user_context: UserContext = field(default_factory=UserContext)
    location_history: List[LocationContext] = field(default_factory=list)
    
    # ========== BARU: Intimacy Detail ==========
    intimacy_detail: IntimacyDetail = field(default_factory=IntimacyDetail)
    role_display_name: str = ""

    def clamp(self) -> None:
        """Clamp semua sub-state ke rentang aman."""

        self.emotions.clamp()
        self.relationship.clamp()

    # ========== BARU: Memory Methods ==========
    
    def add_conversation_turn(self, turn: ConversationTurn, max_memory: int = 30) -> None:
        self.conversation_memory.append(turn)
        if len(self.conversation_memory) > max_memory:
            self.conversation_memory.pop(0)
        self.current_sequence = turn.scene_sequence
    
    def add_scene_turn(self, turn: SceneTurn, max_memory: int = 50) -> None:
        self.scene_memory.append(turn)
        if len(self.scene_memory) > max_memory:
            self.scene_memory.pop(0)
    
    def get_scene_summary(self) -> str:
        if not self.scene_memory:
            return "Belum ada adegan. Mas baru datang."
        
        lines = ["URUTAN ADEGAN YANG SUDAH TERJADI:"]
        for i, turn in enumerate(self.scene_memory, 1):
            feeling = turn.role_feeling[:80] if turn.role_feeling else "(perasaan tidak dicatat)"
            lines.append(f"  {i}. {turn.sequence.value} - {turn.location}")
            lines.append(f"     Perasaan: {feeling}")
        return "\n".join(lines)
    
    def get_last_scene(self) -> Optional[SceneTurn]:
        return self.scene_memory[-1] if self.scene_memory else None
    
    def get_phase_description(self) -> str:
        phase_map = {
            IntimacyPhase.AWAL: "Masih malu-malu, belum berani inisiatif.",
            IntimacyPhase.DEKAT: "Sudah nyaman, mulai berani mendekat atau menyentuh kecil.",
            IntimacyPhase.INTIM: "Sudah sering pelukan, napas beradu, tubuh saling menempel.",
            IntimacyPhase.VULGAR: "Sedang dalam aktivitas seksual intens (level 10-12).",
            IntimacyPhase.AFTER: "Setelah intim, suasana tenang, hangat, saling memeluk.",
        }
        return phase_map.get(self.intimacy_phase, "Tahap awal perkenalan.")
    
    def get_next_sequence(self, user_text: str) -> SceneSequence:
        text = user_text.lower()
        
        order = [
            SceneSequence.USER_DATANG,
            SceneSequence.NGOBROL,
            SceneSequence.MENDEKAT,
            SceneSequence.SENTUHAN_PERTAMA,
            SceneSequence.PELUKAN,
            SceneSequence.CIUMAN,
            SceneSequence.PETTING,
            SceneSequence.SEX_MULAI,
            SceneSequence.SEX_INTENS,
            SceneSequence.CLIMAX,
            SceneSequence.AFTER_SEX,
            SceneSequence.TIDUR,
            SceneSequence.PAGI_HARI,
        ]
        
        if self.current_sequence is None:
            return SceneSequence.USER_DATANG
        
        try:
            current_idx = order.index(self.current_sequence)
        except ValueError:
            return SceneSequence.USER_DATANG
        
        if any(kw in text for kw in ["datang", "mampir", "sampe", "mau ke rumah"]):
            return SceneSequence.USER_DATANG
        if any(kw in text for kw in ["ngobrol", "cerita", "bicara"]):
            return order[min(current_idx + 1, len(order)-1)]
        if any(kw in text for kw in ["dekat", "mepet", "duduk", "sebelahan"]):
            return order[min(current_idx + 1, len(order)-1)]
        if any(kw in text for kw in ["nyentuh", "tersentuh", "kena", "pegang tangan"]):
            return order[min(current_idx + 1, len(order)-1)]
        if any(kw in text for kw in ["peluk", "rangkul", "pelukan"]):
            return order[min(current_idx + 1, len(order)-1)]
        if any(kw in text for kw in ["cium", "kiss", "ciuman"]):
            return order[min(current_idx + 1, len(order)-1)]
        if any(kw in text for kw in ["petting", "pegang", "remas"]):
            return order[min(current_idx + 1, len(order)-1)]
        if any(kw in text for kw in ["masuk", "ngewe", "sex", "kontol", "memek"]):
            return order[min(current_idx + 2, len(order)-1)]
        if any(kw in text for kw in ["climax", "keluar", "sampe", "habis", "enak banget"]):
            return order[min(current_idx + 1, len(order)-1)]
        if any(kw in text for kw in ["selesai", "capek", "tidur", "istirahat"]):
            return order[min(current_idx + 1, len(order)-1)]
        
        return order[min(current_idx, len(order)-1)]

     # ========== TAMBAHKAN INI UNTUK LOKASI ==========
    current_location_id: str = "ruang_tamu"
    current_location_name: str = "Ruang Tamu"
    current_location_desc: str = "Ruang tamu dengan sofa nyaman, TV menyala pelan"
    current_location_is_private: bool = False
    current_location_ambience: str = "suasana hangat, lampu tidak terlalu terang"
    current_location_risk: str = "medium"  # low, medium, high

    # ========== HANDUK ==========
    handuk_tersedia: bool = False
    handuk_dikasih: bool = False
    
    # ========== BARU: Location Methods ==========
    
    def set_location(self, location: LocationContext) -> None:
        if self.current_location:
            self.location_history.append(self.current_location)
        self.current_location = location
    
    def get_location_description(self) -> str:
        if not self.current_location:
            return "belum ada lokasi yang ditentukan"
        desc = self.current_location.name
        if self.current_location.notes:
            desc += f" ({self.current_location.notes})"
        return desc
    
    def update_user_info(self, user_text: str) -> None:
        import re
        text = user_text.lower()
        
        # Deteksi nama
        if "namaku" in text or "nama saya" in text:
            match = re.search(r'namaku\s+(\w+)', text)
            if not match:
                match = re.search(r'nama saya\s+(\w+)', text)
            if match:
                self.user_context.preferred_name = match.group(1)
        
        # Deteksi pekerjaan
        if "kerja sebagai" in text:
            match = re.search(r'kerja sebagai\s+([^.]+)', text)
            if match:
                self.user_context.job = match.group(1).strip()
        
        # Deteksi apartemen
        if "apartemen" in text or "apartemenku" in text:
            self.user_context.has_apartment = True
            if "lantai" in text:
                match = re.search(r'lantai\s+(\d+)', text)
                if match:
                    self.user_context.apartment_note = f"lantai {match.group(1)}"
            if "view" in text or "pemandangan" in text:
                if self.user_context.apartment_note:
                    self.user_context.apartment_note += ", view kota"
                else:
                    self.user_context.apartment_note = "view kota"
    
    # ========== BARU: Intimacy Detail Methods ==========
    
    def update_intimacy_from_text(self, user_text: str, response_text: str) -> None:
        text = (user_text + " " + response_text).lower()
        
        position_map = {
            "misionaris": SexPosition.MISSIONARY, "misi": SexPosition.MISSIONARY,
            "di atas": SexPosition.COWGIRL, "cowgirl": SexPosition.COWGIRL,
            "naik ke atas": SexPosition.COWGIRL, "membelakangi": SexPosition.REVERSE_COWGIRL,
            "reverse": SexPosition.REVERSE_COWGIRL, "dari belakang": SexPosition.DOGGY,
            "doggy": SexPosition.DOGGY, "menyamping": SexPosition.SPOON,
            "spoon": SexPosition.SPOON, "sendok": SexPosition.SPOON,
            "duduk": SexPosition.SITTING, "berdiri": SexPosition.STANDING,
            "di tepi": SexPosition.EDGE, "tepi kasur": SexPosition.EDGE,
            "telungkup": SexPosition.PRONE, "di kursi": SexPosition.CHAIR,
            "di tembok": SexPosition.WALL, "di mobil": SexPosition.CAR, "mobil": SexPosition.CAR,
        }
        
        for keyword, position in position_map.items():
            if keyword in text:
                self.intimacy_detail.position = position
                break
        
        if any(kw in text for kw in ["pegang rambut", "dorong", "paksa", "suruh", "perintah"]):
            if "aku" in response_text and any(kw in response_text for kw in ["pegang", "dorong", "suruh"]):
                self.intimacy_detail.dominance = Dominance.ROLE_DOMINANT
            else:
                self.intimacy_detail.dominance = Dominance.USER_DOMINANT
        elif any(kw in text for kw in ["saling", "bergantian", "gantian"]):
            self.intimacy_detail.dominance = Dominance.SWITCH
        
        if any(kw in text for kw in ["foreplay", "pemanasan", "elus"]):
            self.intimacy_detail.intensity = IntimacyIntensity.FOREPLAY
        elif any(kw in text for kw in ["pegang", "remas", "sentuk"]):
            self.intimacy_detail.intensity = IntimacyIntensity.PETTING
        elif any(kw in text for kw in ["hisap", "jilat", "oral", "ngocok"]):
            if any(kw in text for kw in ["kontol", "p*nis", "batang"]):
                self.intimacy_detail.intensity = IntimacyIntensity.ORAL_GIVING
            else:
                self.intimacy_detail.intensity = IntimacyIntensity.ORAL_RECEIVING
        elif any(kw in text for kw in ["masuk", "penetrasi", "colok"]):
            self.intimacy_detail.intensity = IntimacyIntensity.PENETRATION
        elif any(kw in text for kw in ["hentak", "goyang", "pantat", "pinggul", "gerak"]):
            self.intimacy_detail.intensity = IntimacyIntensity.THRUSTING
        elif any(kw in text for kw in ["climax", "keluar", "sampe", "habis", "enak banget"]):
            self.intimacy_detail.intensity = IntimacyIntensity.CLIMAX
        elif any(kw in text for kw in ["selesai", "capek", "tidur", "istirahat"]):
            self.intimacy_detail.intensity = IntimacyIntensity.AFTER
        
        actions = []
        if "menarik" in text or "narik" in text:
            actions.append("menarik")
        if "mendorong" in text:
            actions.append("mendorong")
        if "memutar" in text:
            actions.append("memutar")
        if "membalik" in text:
            actions.append("membalikkan badan")
        if actions:
            self.intimacy_detail.last_action = ", ".join(actions)
        
        feelings = []
        if "enak" in text:
            feelings.append("enak")
        if "panas" in text:
            feelings.append("panas")
        if "basah" in text:
            feelings.append("basah")
        if "keras" in text:
            feelings.append("keras")
        if "lemas" in text:
            feelings.append("lemas")
        if feelings:
            self.intimacy_detail.last_pleasure = ", ".join(feelings)
            
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

