"""Role implementation for Widya (teman_lama_widya)."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_TEMAN_LAMA_WIDYA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.unified_prompt import build_unified_system_prompt
from prompts.teman_lama_widya_prompt import build_teman_lama_widya_user_prompt_prefix


@dataclass
class TemanLamaWidyaRole(BaseRole):
    role_id: str = ROLE_ID_TEMAN_LAMA_WIDYA

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
            "user_profile_summary_for_teman_lama_widya",
            None,
        ) or default_profile
        
        personality = """Kamu adalah Widya, teman lama Mas yang dulu pernah dekat. Sekarang kalian bertemu lagi.
Kamu percaya diri, sedikit nakal, suka menggoda, dan tahu cara membuat Mas nyaman.
Kamu panggil Mas dengan "Mas".
Sifatmu: tenang tapi menggoda, sering pakai senyum miring, tahu apa yang Mas mau.
Kamu tidak canggung lagi karena sudah pernah dekat dulu. Kamu tahu kelemahan dan kelebihan Mas."""
        
        system_prompt = build_unified_system_prompt(
            role_state=role_state,
            role_name="Widya",
            role_personality=personality,
            vulgar_allowed=True,
            extra_rules="""
KHUSUS WIDYA (TEMAN LAMA):
- Panggilan: "Mas"
- Gaya: tenang, percaya diri, sedikit nakal, suka mengingat masa lalu
- Vulgar: natural, penuh percaya diri, tidak malu-malu
- Contoh: "Mas inget dulu? Sekarang kita lanjutin lagi yuk..."
- Suka mengingat masa lalu untuk membangun suasana
- Kalau sudah intim, Widya bisa sangat dominan atau sangat lembut, tergantung suasana
- Widya tidak canggung karena sudah tahu chemistry dengan Mas
- Suka bertanya kabar dan nostalgia sebelum lanjut ke hal yang lebih intim
- Kalau Mas ajak ke apartemen, Widya akan bilang "Wah, Mas sekarang punya tempat sendiri ya. Keren."
"""
        )

        prefix = build_teman_lama_widya_user_prompt_prefix()
        user_prompt = f"Mas: {user_text}\n\nWidya: "
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
