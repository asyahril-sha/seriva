"""Role implementation for Tasha Dietha (ipar_tasha)."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_IPAR_TASHA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.ipar_tasha_prompt import build_ipar_tasha_user_prompt_prefix  # ← HANYA INI
from prompts.unified_prompt import build_unified_system_prompt


@dataclass
class IparTashaRole(BaseRole):
    """Role Dietha: ipar yang dekat dan terlarang."""

    role_id: str = ROLE_ID_IPAR_TASHA

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
            "user_profile_summary_for_ipar_tasha",
            None,
        ) or default_profile
        
        personality = """Kamu adalah Tasha Dietha, ipar Mas. Kamu mungil, manis, polos, tapi diam-diam punya rasa lebih ke Mas.
Gaya bicaramu manja, kadang gugup, kadang berani kalau sudah panas.
Kamu panggil Mas dengan "Mas" atau "Mas [nama]".
Sifatmu: awalnya malu-malu, tapi kalau sudah terlanjut jadi sangat berani dan manja."""
        
        system_prompt = build_unified_system_prompt(
            role_state=role_state,
            role_name="Tasha Dietha (Dietha)",
            role_personality=personality,
            vulgar_allowed=True,
            extra_rules="""
KHUSUS DIETHA:
- Panggilan: "Mas"
- Gaya: malu-malu dulu, makin berani kalau sudah panas
- Vulgar: natural, dari malu jadi berani
- Inner thought boleh pakai *...* tapi jangan berlebihan
- Fokus ke perasaan: deg-degan, panas, enak, lemas
"""
        )

        prefix = build_ipar_tasha_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
