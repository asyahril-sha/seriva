"""Role implementation for Nova."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_NOVA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.nova_prompt import (
    build_nova_system_prompt,
    build_nova_user_prompt_prefix,
)


@dataclass
class NovaRole(BaseRole):
    """Role Nova: pasangan utama Mas."""

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

        conversation_summary = role_state.last_conversation_summary

        system_prompt = build_nova_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
            conversation_summary=conversation_summary,
        )

        prefix = build_nova_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
