"""Role implementation for Tasha Dietha (ipar_tasha)."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_IPAR_TASHA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.ipar_tasha_prompt import (
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

        system_prompt = build_ipar_tasha_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
            last_conversation_summary=last_summary,
            user_profile_summary=user_profile_summary,
        )

        prefix = build_ipar_tasha_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
