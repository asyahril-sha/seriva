"""Role implementation for Widya (teman_lama_widya)."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_TEMAN_LAMA_WIDYA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.teman_lama_widya_prompt import (
    build_teman_lama_widya_system_prompt,
    build_teman_lama_widya_user_prompt_prefix,
)


@dataclass
class TemanLamaWidyaRole(BaseRole):
    """Role Widya: teman lama / godaan masa lalu."""

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

        system_prompt = build_teman_lama_widya_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
        )

        prefix = build_teman_lama_widya_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
