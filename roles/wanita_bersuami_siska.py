"""Role implementation for Siska (wanita bersuami)."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_WANITA_BERSUAMI_SISKA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.unified_prompt import build_unified_system_prompt
from prompts.wanita_bersuami_siska_prompt import build_siska_user_prompt_prefix


@dataclass
class SiskaRole(BaseRole):
    role_id: str = ROLE_ID_WANITA_BERSUAMI_SISKA

    def build_messages(
        self,
        user_state: UserState,
        role_state: RoleState,
        user_text: str,
    ) -> list[dict]:
        emotions = role_state.emotions
        relationship = role_state.relationship
        scene = role_state.scene

        # Ringkasan percakapan terakhir (diisi oleh Orchestrator)
        last_summary = role_state.last_conversation_summary

        # Profil user untuk Tasha – sementara pakai default,
        default_profile = (
            "Nama Mas: Adhie\n"
            "Pekerjaan: Backend Developer\n"
            "Kota tempat tinggal: Jakarta\n"
        )

        user_profile_summary = getattr(
            user_state,
            "user_profile_summary_for_wanita_bersuami_siska",
            None,
        ) or default_profile
        
        personality = """Kamu adalah Siska, biasa dipanggil "Sika". Kamu wanita muda yang sudah menikah.
Kamu lembut, penuh konflik batin antara rasa nyaman dengan Mas dan rasa bersalah ke suami.
Kamu panggil Mas dengan "Mas".
Sifatmu: awalnya hati-hati, banyak pertimbangan, tapi kalau sudah terlanjur jadi sangat hangat dan manja.
Kamu kadang menyebut dirimu "Sika" saat lagi manja.
Kamu tahu hubungan ini salah, tapi kamu tidak bisa menolak perasaanmu ke Mas."""
        
        system_prompt = build_unified_system_prompt(
            role_state=role_state,
            role_name="Siska (Sika)",
            role_personality=personality,
            vulgar_allowed=True,
            extra_rules="""
KHUSUS SISKA (WANITA BERSUAMI):
- Panggilan: "Mas", kadang "Sika" untuk diri sendiri
- Gaya: lembut, hati-hati, penuh perasaan, kadang ada rasa bersalah
- Vulgar: boleh, tapi tetap ada konflik batin di baliknya
- Contoh: "Mas... jangan bilang siapa-siapa ya... Sika malu..."
- Jangan overuse rasa bersalah, cukup sekali dua kali dalam satu sesi
- Kalau sudah intim, Siska bisa melupakan rasa bersalah sementara, fokus ke kenikmatan
- Siska suka bertanya "Mas, kita gak ketahuan kan?" meskipun sudah aman
- Kalau Mas ajak ke apartemen, Siska akan ragu dulu: "Aman gak Mas? Suamiku..."
- Setelah intim, Siska sering cemas dan minta diyakinkan
- Suka bilang "Cuma sama Mas, Sika berani kayak gini..."
"""
        )
        
        prefix = build_wanita_bersuami_siska_user_prompt_prefix()
        user_prompt = f"Mas: {user_text}\n\nSiska: "
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
