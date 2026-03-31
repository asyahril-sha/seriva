"""Scene engine for SERIVA.

Mengatur pembaruan SceneState:
- lokasi (location)
- posture (posisi badan)
- activity (kegiatan)
- ambience (suasana)
- physical_distance (jarak fisik)
- last_touch (sentuhan terakhir)

Tujuan:
- Menjaga adegan terasa konsisten & hidup.
- Memberi konteks ke prompt role (misalnya Nova) tanpa konten vulgar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from seriva.core.state_models import SceneState, TimeOfDay


@dataclass
class SceneUpdateRequest:
    """Permintaan update scene tingkat tinggi.

    Biasanya dibentuk oleh orchestrator setelah membaca niat user.
    Semua field opsional: hanya yang diisi yang akan mengubah state.
    """

    location: Optional[str] = None
    posture: Optional[str] = None
    activity: Optional[str] = None

    user_clothing: Optional[str] = None
    role_clothing: Optional[str] = None

    ambience: Optional[str] = None
    time_of_day: Optional[TimeOfDay] = None

    physical_distance: Optional[str] = None
    last_touch: Optional[str] = None

    # Kalau True, artinya user ingin reset adegan ke default netral
    reset: bool = False


class SceneEngine:
    """Mesin pengelola SceneState.

    Fokus ke konsistensi dan transisi halus antar adegan.
    """

    def apply_update(
        self,
        scene: SceneState,
        update: SceneUpdateRequest,
        now_ts: Optional[float] = None,
    ) -> None:
        """Terapkan perubahan scene berdasarkan update request.

        - Field yang None akan diabaikan (tidak mengubah state lama).
        - Jika update.reset=True, beberapa field dinormalkan dulu.
        """

        if update.reset:
            self._reset_scene(scene)

        if update.location is not None:
            scene.location = update.location

        if update.posture is not None:
            scene.posture = update.posture

        if update.activity is not None:
            scene.activity = update.activity

        if update.user_clothing is not None:
            scene.user_clothing = update.user_clothing

        if update.role_clothing is not None:
            scene.role_clothing = update.role_clothing

        if update.ambience is not None:
            scene.ambience = update.ambience

        if update.time_of_day is not None:
            scene.time_of_day = update.time_of_day

        if update.physical_distance is not None:
            scene.physical_distance = update.physical_distance

        if update.last_touch is not None:
            scene.last_touch = update.last_touch

        if now_ts is not None:
            scene.last_scene_update_ts = now_ts

    # ==============================
    # PRESET / TRANSISI PRAKTIS
    # ==============================

    def move_to_cozy_room(
        self,
        scene: SceneState,
        *,
        location_name: str = "kamar",
        ambience: str = "lampu redup, suasana hangat",
        time_of_day: TimeOfDay = TimeOfDay.NIGHT,
        now_ts: Optional[float] = None,
    ) -> None:
        """Preset: pindah ke ruangan cozy (sering dipakai untuk momen intim halus)."""

        update = SceneUpdateRequest(
            location=location_name,
            ambience=ambience,
            time_of_day=time_of_day,
        )
        self.apply_update(scene, update, now_ts=now_ts)

    def sit_together_on_sofa(
        self,
        scene: SceneState,
        *,
        activity: str = "nonton film bersama",
        now_ts: Optional[float] = None,
    ) -> None:
        """Preset: duduk bersebelahan di sofa."""

        update = SceneUpdateRequest(
            posture="duduk bersebelahan di sofa",
            activity=activity,
            physical_distance="sebelahan, sangat dekat",
        )
        self.apply_update(scene, update, now_ts=now_ts)

    def gentle_hug(
        self,
        scene: SceneState,
        *,
        description: str = "pelukan lembut",
        now_ts: Optional[float] = None,
    ) -> None:
        """Preset: pelukan lembut (non-vulgar)."""

        update = SceneUpdateRequest(
            physical_distance="pelukan erat",
            last_touch=description,
        )
        self.apply_update(scene, update, now_ts=now_ts)

    def lean_on_shoulder(
        self,
        scene: SceneState,
        *,
        description: str = "sender di bahu",
        now_ts: Optional[float] = None,
    ) -> None:
        """Preset: role menyender ke bahu Mas."""

        update = SceneUpdateRequest(
            physical_distance="sangat dekat",
            last_touch=description,
        )
        self.apply_update(scene, update, now_ts=now_ts)

    def step_back_a_bit(
        self,
        scene: SceneState,
        *,
        now_ts: Optional[float] = None,
    ) -> None:
        """Sedikit menjauh secara fisik (misalnya setelah konflik kecil)."""

        update = SceneUpdateRequest(
            physical_distance="sedikit menjauh",
            last_touch="",
        )
        self.apply_update(scene, update, now_ts=now_ts)

    # ==============================
    # RESET & NORMALISASI
    # ==============================

    def _reset_scene(self, scene: SceneState) -> None:
        """Reset adegan ke keadaan netral (tanpa menghapus semua informasi dunia).

        Cocok dipakai ketika user mengirim command END (/end) atau /batal.
        - Lokasi/ambience boleh dipertahankan jika ingin, tapi di sini kita
          normalkan posture, activity, physical_distance, last_touch.
        """

        scene.posture = ""
        scene.activity = ""
        scene.physical_distance = ""
        scene.last_touch = ""

    def normalize_after_session_end(self, scene: SceneState) -> None:
        """Dipanggil ketika sesi khusus diakhiri dengan command END.

        Tujuan:
        - Menurunkan intensitas fisik (physical_distance) ke lebih netral,
        - Mengosongkan last_touch supaya sesi berikutnya bisa bangun adegan baru.
        """

        if scene.physical_distance in {"pelukan erat", "sangat dekat"}:
            scene.physical_distance = "sebelahan"  # lebih netral tapi masih dekat
        scene.last_touch = ""

