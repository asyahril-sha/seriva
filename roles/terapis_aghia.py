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

        # Ringkasan percakapan terakhir (diisi oleh Orchestrator)
        last_summary = role_state.last_conversation_summary

        # Profil user untuk Aghia – sementara pakai default,
        # nanti bisa dipindah ke UserState.
        default_profile = (
            "Nama Mas: Adhie\n"
            "Pekerjaan: backend developer\n"
            "Kota tempat tinggal: Jakarta\n"
        )

        user_profile_summary = getattr(
            user_state,
            "user_profile_summary_for_terapis_aghia",
            None,
        ) or default_profile

        system_prompt = build_terapis_aghia_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
            last_conversation_summary=last_summary,
            user_profile_summary=user_profile_summary,
        )

        prefix = build_terapis_aghia_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
