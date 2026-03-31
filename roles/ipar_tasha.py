"""Role implementation for Tasha Dietha (ipar_tasha)."""

from __future__ import annotations

from dataclasses import dataclass

from seriva.config.constants import ROLE_ID_IPAR_TASHA
from seriva.core.state_models import RoleState, UserState
from seriva.roles.base_role import BaseRole
from seriva.prompts.ipar_tasha_prompt import (
    build_ipar_tasha_system_prompt,
    build_ipar_tasha_user_prompt_prefix,
)


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

        system_prompt = build_ipar_tasha_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
        )

        prefix = build_ipar_tasha_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
