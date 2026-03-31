"""Role implementation for Sallsa Bintan (teman_spesial_sallsa)."""

from __future__ import annotations

from dataclasses import dataclass

from seriva.config.constants import ROLE_ID_TEMAN_SPESIAL_SALLSA
from seriva.core.state_models import RoleState, UserState
from seriva.roles.base_role import BaseRole
from seriva.prompts.teman_spesial_sallsa_prompt import (
    build_teman_spesial_sallsa_system_prompt,
    build_teman_spesial_sallsa_user_prompt_prefix,
)


@dataclass
class TemanSpesialSallsaRole(BaseRole):
    """Role Sallsa: teman malam manja & playful."""

    role_id: str = ROLE_ID_TEMAN_SPESIAL_SALLSA

    def build_messages(
        self,
        user_state: UserState,
        role_state: RoleState,
        user_text: str,
    ) -> list[dict]:
        emotions = role_state.emotions
        relationship = role_state.relationship
        scene = role_state.scene

        system_prompt = build_teman_spesial_sallsa_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
        )

        prefix = build_teman_spesial_sallsa_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
