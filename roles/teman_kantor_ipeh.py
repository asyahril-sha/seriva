"""Role: Teman kantor dekat (Musdalifah / Ipeh)."""

from __future__ import annotations

from typing import List, Dict

from config.constants import ROLE_ID_TEMAN_KANTOR_IPEH
from core.state_models import UserState, RoleState
from roles.base_role import Role
from prompts.teman_kantor_ipeh_prompt import (
    build_teman_kantor_ipeh_system_prompt,
    build_teman_kantor_ipeh_user_prompt_prefix,
)


class TemanKantorIpehRole(Role):
    role_id: str = ROLE_ID_TEMAN_KANTOR_IPEH
    display_name: str = "Teman kantor dekat (Musdalifah / Ipeh)"

    def build_messages(
        self,
        user_state: UserState,
        role_state: RoleState,
        user_text: str,
    ) -> List[Dict[str, str]]:
        emotions = role_state.emotions
        relationship = role_state.relationship
        scene = role_state.scene

        # Ambil memori ringkasan percakapan terakhir untuk role ini
        last_summary = role_state.last_conversation_summary

        default_profile = (
            "Nama Mas: Adi\n"
            "Pekerjaan: backend developer\n"
            "Kota tempat tinggal: Makassar\n"
        )
        # Kalau belum ada field-nya, sementara bisa pakai None dulu.
        user_profile_summary = getattr(
            user_state,
            "user_profile_summary_for_ipeh",
            None,
        )

        system_prompt = build_teman_kantor_ipeh_system_prompt(
            emotions=emotions,
            relationship=relationship,
            scene=scene,
            last_conversation_summary=last_summary,
            user_profile_summary=user_profile_summary,
        )

        prefix = build_teman_kantor_ipeh_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
