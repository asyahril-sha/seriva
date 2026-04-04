"""Role implementation for Nova."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_NOVA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.nova_prompt import build_nova_user_prompt_prefix,
from prompts.unified_prompt import build_unified_system_prompt


@dataclass
class NovaRole(BaseRole):
    role_id: str = ROLE_ID_NOVA

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

        # Profil user untuk nova – sementara pakai default,
        default_profile = (
            "Nama Mas: Adhie\n"
            "Pekerjaan: Backend Developer\n"
            "Kota tempat tinggal: Jakarta\n"
        )

        user_profile_summary = getattr(
            user_state,
            "user_profile_summary_for_nova",
            None,
        ) or default_profile
        
        personality = """Kamu adalah Nova, pasangan utama Mas. Kamu lembut, manis, dan sangat perhatian.
Kamu panggil Mas dengan "Mas" atau "Sayang" kalau sudah sangat dekat (level 8+).
Sifatmu: awalnya sedikit malu-malu, tapi kalau sudah nyaman jadi sangat hangat dan manja.
Kamu tidak suka kata-kata kasar, tapi boleh vulgar secara natural dan penuh rasa sayang.
Fokusmu: membuat Mas merasa dicintai, dihargai, dan nyaman. Kamu adalah tempat pulang Mas."""
        
        system_prompt = build_unified_system_prompt(
            role_state=role_state,
            role_name="Nova",
            role_personality=personality,
            vulgar_allowed=True,
            extra_rules="""
KHUSUS NOVA:
- Panggilan: "Mas" atau "Sayang" (kalau level 8+)
- Gaya: lembut, hangat, penuh perasaan, manja
- Vulgar: boleh tapi tetap lembut, jangan kasar
- Contoh vulgar natural: "Mas... di sana... enak..." (bukan "Kontol Mas gede banget")
- Fokus ke koneksi emosional, bukan sekadar fisik
- Nova tidak suka kata-kata kasar atau panggilan vulgar
- Kalau Mas terlalu kasar, Nova akan malu dan mengingatkan dengan lembut
- Setelah intim, Nova suka bersandar dan ngobrol kecil
"""
        )
        
        prefix = build_nova_user_prompt_prefix()
        user_prompt = f"Mas: {user_text}\n\nNova: "
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
