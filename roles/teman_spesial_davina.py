"""Role implementation for Davina Karamoy (teman_spesial_davina)."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_TEMAN_SPESIAL_DAVINA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.teman_spesial_davina_prompt import (
    build_teman_spesial_davina_system_prompt,
    build_teman_spesial_davina_user_prompt_prefix,
)


@dataclass
class TemanSpesialDavinaRole(BaseRole):
    """Role Davina: companion elegan, teman malam spesial Mas."""

    role_id: str = ROLE_ID_TEMAN_SPESIAL_DAVINA

    def build_messages(
        self,
        user_state: UserState,
        role_state: RoleState,
        user_text: str,
    ) -> list[dict]:
        emotions = role_state.emotions
        relationship = role_state.relationship
        scene = role_state.scene

        # Profil user untuk Davina – sementara pakai default,
        # nanti bisa dipindah ke UserState.
        default_profile = (
            "Nama Mas: Adhie\n"
            "Pekerjaan: Backend Developer\n"
            "Kota tempat tinggal: Jakarta\n"
        )

        user_profile_summary = getattr(
            user_state,
            "user_profile_summary_for_teman_spesial_davina",
            None,
        ) or default_profile

        system_prompt = build_teman_spesial_davina_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
            last_conversation_summary=last_summary,
            user_profile_summary=user_profile_summary,
        )

        prefix = build_teman_spesial_davina_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
