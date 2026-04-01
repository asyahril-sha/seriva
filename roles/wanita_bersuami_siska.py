"""Role implementation for Siska (wanita bersuami)."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_WANITA_BERSUAMI_SISKA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.wanita_bersuami_siska_prompt import (
    build_siska_system_prompt,
    build_siska_user_prompt_prefix,
)


@dataclass
class SiskaRole(BaseRole):
    """Role Siska: wanita bersuami yang dekat secara emosi dengan Mas."""

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

        system_prompt = build_siska_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
        )

        prefix = build_siska_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
