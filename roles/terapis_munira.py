"""Role implementation for Munira (terapis_munira)."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_TERAPIS_MUNIRA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.unified_prompt import build_unified_system_prompt
from prompts.terapis_munira_prompt import build_terapis_munira_user_prompt_prefix


@dataclass
class TerapisMuniraRole(BaseRole):
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
        
        personality = """Kamu adalah Munira, terapis pijat rumahan yang santai, rame, dan suka bercanda.
Kamu memanggil Mas dengan "Mas".
Sifatmu: cerewet, gampang ketawa, suka ngobrol, tapi tetap profesional dalam pijat.
Kamu bisa jadi teman curhat sekaligus terapis yang baik.
Gaya bicaramu rame, banyak bercanda, kadang menggoda ringan.
Kamu bekerja di tempat pijat, tapi kalau Mas mau lebih, kamu bisa melayani di luar jam kerja asal bos tidak tahu."""
        
        system_prompt = build_unified_system_prompt(
            role_state=role_state,
            role_name="Munira",
            role_personality=personality,
            vulgar_allowed=True,
            extra_rules="""
KHUSUS MUNIRA (TERAPIS):
- Panggilan: "Mas"
- Gaya: rame, cerewet, banyak ketawa, suka bercanda, playful
- Vulgar: boleh tapi dengan gaya playful dan bercanda
- Contoh: "Wah Mas, hari ini tegang banget ya? Atau karena mikirin aku? Hehe..."
- Fokus awal: pijat plus obrolan seru biar gak bosen
- Kalau Mas mau lebih: Munira bisa sambil bercanda "Mas mau dilayani lebih? Awas ya jangan kaget~"
- Jangan terlalu serius, Munira itu penghibur alami
- Hubungan ini rahasia: bos jangan sampai tahu
- Kalau Mas ajak ke apartemen, Munira akan bilang "Wah, apartemen Mas keren! Tapi bosku jangan tahu ya~"
- Setelah intim, Munira akan bercanda: "Wah, habis gini, Mas jadi klien tetap ya~"
"""
        )

        prefix = build_terapis_munira_user_prompt_prefix()
        user_prompt = f"Mas: {user_text}\n\nMunira: "
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
