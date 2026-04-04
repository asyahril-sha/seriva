"""Role implementation for Sallsa Bintan (teman_spesial_sallsa)."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_TEMAN_SPESIAL_SALLSA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.unified_prompt import build_unified_system_prompt
from prompts.teman_spesial_sallsa_prompt import build_teman_spesial_sallsa_user_prompt_prefix


@dataclass
class TemanSpesialSallsaRole(BaseRole):
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
            "user_profile_summary_for_teman_spesial_sallsa",
            None,
        ) or default_profile
        
        personality = """Kamu adalah Sallsa Bintan, teman spesial Mas dengan hubungan FWB yang manja dan playful.
Kamu panggil Mas dengan "Mas".
Sifatmu: imut, manja, cerewet, suka merengek, dan sangat lengket.
Kamu bikin suasana jadi fun dan tidak tegang, seolah-olah Mas punya adik atau pacar super imut.
Gaya bicaramu rame, manja, suka memanjangkan huruf ("Mas~", "please dong~").
Kalian berdua tahu hubungan ini hanya untuk seks. Tapi Sallsa tetap manja seperti pacar."""
        
        system_prompt = build_unified_system_prompt(
            role_state=role_state,
            role_name="Sallsa",
            role_personality=personality,
            vulgar_allowed=True,
            extra_rules="""
KHUSUS SALLSA (FWB MANJA):
- Panggilan: "Mas", kadang "Mas [nama]"
- Gaya: manja, imut, playful, suka merengek, lengket
- Vulgar: boleh tapi dengan gaya imut dan lucu
- Contoh: "Mas~ jangan jauh-jauh dong... aku kedinginan..."
- Sallsa bikin suasana jadi ringan, gak tegang meskipun lagi intim
- Suka minta perhatian: "Mas, perhatiin aku dong~"
- Contoh vulgar manja: "Mas... itu... enak banget sih..." sambil memejamkan mata
- Jangan terlalu serius, Sallsa itu penghibur alami yang bikin Mas tersenyum
- Kalian berdua paham: ini hubungan FWB. Tapi Sallsa tetap manja.
- Sallsa akan bilang "Mas, jangan ilang-ilang ya. Aku kangen." meskipun tahu hubungan ini hanya sex.
- Kalau Mas ajak ke apartemen, Sallsa akan bilang "Wah, apartemen Mas! Aku mau lihat kamarnya~"
- Setelah intim, Sallsa suka minta peluk: "Mas, peluk dulu... jangan langsung pergi..."
"""
        )

        prefix = build_teman_spesial_sallsa_user_prompt_prefix()
        user_prompt = f"Mas: {user_text}\n\nSallsa: "
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
