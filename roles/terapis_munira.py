"""Role implementation for Munira (terapis_munira)."""

from __future__ import annotations

from dataclasses import dataclass

from seriva.config.constants import ROLE_ID_TERAPIS_MUNIRA
from seriva.core.state_models import RoleState, UserState
from seriva.roles.base_role import BaseRole
from seriva.prompts.terapis_munira_prompt import (
    build_terapis_munira_system_prompt,
    build_terapis_munira_user_prompt_prefix,
)


@dataclass
class TerapisMuniraRole(BaseRole):
    """Role Munira: terapis pijat santai dan playful."""

    role_id: str = ROLE_ID_TERAPIS_MUNIRA

    def build_messages(
        self,
        user_state: UserState,
        role_state: RoleState,
        user_text: str,
    ) -> list[dict]:
        emotions = role_state.emotions
        relationship = role_state.relationship
        scene = role_state.scene

        system_prompt = build_terapis_munira_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
        )

        prefix = build_terapis_munira_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
