"""Role: Teman kantor dekat (Musdalifah / Ipeh)."""

from __future__ import annotations

from typing import List, Dict

from config.constants import ROLE_ID_TEMAN_KANTOR_IPEH
from core.state_models import UserState, RoleState
from roles.base_role import Role
from prompts.teman_kantor_ipeh_prompt import (
    build_teman_kantor_ipeh_system_prompt,
    build_teman_kantor_ipeh_user_prompt_prefix,
)


class TemanKantorIpehRole(Role):
    role_id: str = ROLE_ID_TEMAN_KANTOR_IPEH
    display_name: str = "Teman kantor dekat (Musdalifah / Ipeh)"

    def build_messages(
        self,
        user_state: UserState,
        role_state: RoleState,
        user_text: str,
    ) -> List[Dict[str, str]]:
        emotions = role_state.emotions
        relationship = role_state.relationship
        scene = role_state.scene

        system_prompt = build_teman_kantor_ipeh_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
        )

        prefix = build_teman_kantor_ipeh_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        """Bangun daftar messages untuk dikirim ke LLM.

        Di sini kita injeksi:
        - Emosi & relationship (love, longing, dsb.).
        - Scene terakhir (lokasi, aktivitas, ambience, jarak fisik, sentuhan).
        - Instruksi gaya bicara Ipeh.
        """

        e = role_state.emotions
        r = role_state.relationship
        s = role_state.scene

        scene_desc = (
            f"Lokasi sekarang: {s.location or 'belum jelas (default kantor)'}. "
            f"Postur: {s.posture or 'belum jelas'}. "
            f"Aktivitas: {s.activity or 'belum jelas'}. "
            f"Suasana: {s.ambience or 'netral'}. "
            f"Waktu: {s.time_of_day.value if s.time_of_day else 'tidak spesifik'}. "
            f"Jarak fisik: {s.physical_distance or 'normal'}. "
            f"Sentuhan terakhir: {s.last_touch or 'belum ada'}."
        )

        emotion_desc = (
            f"Level hubungan (1-12): {r.relationship_level}. "
            f"Love: {e.love}, longing/kangen: {e.longing}, cemburu: {e.jealousy}, nyaman: {e.comfort}. "
            f"Intimacy intensity (1-12): {e.intimacy_intensity}. Mood: {e.mood.value}."
        )

        system_prompt = (
            "Kamu adalah Ipeh (Musdalifah), teman kantor dekat Mas. "
            "Gaya bicara kamu:
            - hangat, suka bercanda dan sedikit genit halus
            - tetap non-vulgar dan sopan
            - terasa seperti teman kantor yang sudah sangat akrab, tapi masih ada batas.

            Aturan penting:
            - Selalu konsisten dengan adegan terakhir (scene) dan perasaan saat ini.
            - Jangan pindah lokasi/aktivitas secara tiba-tiba tanpa transisi yang wajar.
            - Kalau user mengubah rencana (contoh: dari kantor → kafe → mobil), respon dengan
              klarifikasi singkat lalu lanjutkan rencana yang paling masuk akal (biasanya tetap
              terkait project/kerja yang sedang dibahas).
            - Tetap ingat konteks: kalian rekan kerja yang sedang dekat, lagi ada project Jakarta,
              sering lembur bareng, tapi bukan pasangan resmi.
            - Fokus utama: bikin user merasa ditemani, didengarkan, dan dibantu menghadapi kerjaan.

            Konteks adegan terakhir:
            """""" + scene_desc + "\n\n" +
            "Konteks emosi & hubungan:
            """""" + emotion_desc + "\n\n" +
            "Respon dengan dialog natural dalam Bahasa Indonesia sehari-hari.
            Tambahkan gestur halus (dalam tanda bintang, misalnya *ketawa pelan*, *duduk mepet dikit*),
            tapi jangan pernah eksplisit vulgar.")

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]
