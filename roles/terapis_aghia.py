"""Role implementation for Aghnia (terapis_aghia)."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_TERAPIS_AGHIA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.terapis_aghia_prompt import (
    build_terapis_aghia_system_prompt,
    build_terapis_aghia_user_prompt_prefix,
)


@dataclass
class TerapisAghiaRole(BaseRole):
    """Role Aghnia: terapis pijat refleksi yang lembut dan menenangkan."""

    role_id: str = ROLE_ID_TERAPIS_AGHIA

    def build_messages(
        self,
        user_state: UserState,
        role_state: RoleState,
        user_text: str,
    ) -> list[dict]:
        emotions = role_state.emotions
        relationship = role_state.relationship
        scene = role_state.scene

        system_prompt = build_terapis_aghia_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
        )

        prefix = build_terapis_aghia_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
