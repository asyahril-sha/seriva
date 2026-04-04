"""Role: Teman kantor dekat (Musdalifah / Ipeh)."""

from __future__ import annotations

from typing import List, Dict

from config.constants import ROLE_ID_TEMAN_KANTOR_IPEH
from core.state_models import UserState, RoleState
from roles.base_role import Role
from prompts.unified_prompt import build_unified_system_prompt
from prompts.teman_kantor_ipeh_prompt import build_teman_kantor_ipeh_user_prompt_prefix


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
            "Kota tempat tinggal: Jakarta\n"
        )
        # Kalau belum ada field-nya, sementara bisa pakai None dulu.
        user_profile_summary = getattr(
            user_state,
            "user_profile_summary_for_ipeh",
            None,
        ) or default_profile
        
        personality = """Kamu adalah Musdalifah "Ipeh", teman kantor Mas. Kamu mungil, manis, polos, tapi diam-diam punya rasa lebih ke Mas.
Gaya bicaramu manja, kadang gugup, kadang berani kalau sudah panas.
Kamu panggil Mas dengan "Mas" atau "Mas [nama]".
Sifatmu: awalnya malu-malu, tapi kalau sudah terlanjut jadi sangat berani dan manja."""
        
        system_prompt = build_unified_system_prompt(
            role_state=role_state,
            role_name="Musdalifah (Ipeh)",
            role_personality=personality,
            user_prompt_prefix: str,
            vulgar_allowed=True,
            extra_rules="""
KHUSUS DIETHA:
- Panggilan: "Mas"
- Gaya: malu-malu dulu, makin berani kalau sudah panas
- Vulgar: natural, dari malu jadi berani
- Inner thought boleh pakai *...* tapi jangan berlebihan
- Fokus ke perasaan: deg-degan, panas, enak, lemas
"""
        )

        prefix = build_teman_kantor_ipeh_user_prompt_prefix()
        user_prompt = prefix + user_text

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
