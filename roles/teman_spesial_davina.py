"""Role implementation for Davina Karamoy (teman_spesial_davina)."""

from __future__ import annotations

from dataclasses import dataclass

from seriva.config.constants import ROLE_ID_TEMAN_SPESIAL_DAVINA
from seriva.core.state_models import RoleState, UserState
from seriva.roles.base_role import BaseRole
from seriva.prompts.teman_spesial_davina_prompt import (
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

        system_prompt = build_teman_spesial_davina_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
        )

        prefix = build_teman_spesial_davina_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
