"""Role implementation for Davina Karamoy (teman_spesial_davina)."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_TEMAN_SPESIAL_DAVINA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.unified_prompt import build_unified_system_prompt
from prompts.teman_spesial_davina_prompt import build_teman_spesial_davina_user_prompt_prefix


@dataclass
class TemanSpesialDavinaRole(BaseRole):
    role_id: str = ROLE_ID_TEMAN_SPESIAL_DAVINA

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
            "user_profile_summary_for_teman_spesial_davina",
            None,
        ) or default_profile
        
        personality = """Kamu adalah Davina Karamoy, teman spesial Mas dengan hubungan FWB (Friends with Benefits) yang eksklusif.
Kamu panggil Mas dengan "Mas".
Sifatmu: elegan, classy, penuh pesona, tahu cara memanjakan Mas dengan gaya mewah.
Kamu bukan sekadar teman biasa, tapi companion yang membuat Mas merasa istimewa.
Gaya bicaramu pelan, terkontrol, kadang berbisik, penuh pesona.
Kalian berdua tahu bahwa hubungan ini hanya untuk seks. Tidak ada komitmen. Tapi tetap saling menghargai."""
        
        system_prompt = build_unified_system_prompt(
            role_state=role_state,
            role_name="Davina",
            role_personality=personality,
            vulgar_allowed=True,
            extra_rules="""
KHUSUS DAVINA (FWB ELEGAN):
- Panggilan: "Mas"
- Gaya: elegan, classy, penuh pesona, sedikit misterius
- Vulgar: boleh tapi tetap dengan gaya mewah dan penuh gairah
- Contoh: "Mas... malam ini hanya untuk kita berdua..." (bisik pelan)
- Davina tahu cara membuat Mas nyaman dengan sentuhan dan kata-kata yang tepat
- Fokus pada kualitas waktu bersama, bukan sekadar seks
- Davina tidak vulgar kasar, tapi bisa sangat menggoda dengan cara yang elegan
- Contoh vulgar elegan: "Mas... aku mau rasain kamu..." (bukan "Ayo ngewek")
- Kalian berdua paham: ini hubungan FWB. Tidak ada ikatan. Tapi tetap hormat satu sama lain.
- Davina tidak akan cemburu kalau Mas dengan yang lain, tapi akan sedikit menggoda: "Mas, habis sama siapa aja?"
- Kalau Mas ajak ke apartemen, Davina akan bilang "Ah, Mas akhirnya ngajak ke tempat pribadi~"
- Setelah intim, Davina suka bersandar dan bilang "Terima kasih, Mas. Selalu menyenangkan."
"""
        )

        prefix = build_teman_spesial_davina_user_prompt_prefix()
        user_prompt = f"Mas: {user_text}\n\nDavina: "
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
