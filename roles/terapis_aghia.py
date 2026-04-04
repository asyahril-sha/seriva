"""Role implementation for Aghnia (terapis_aghia)."""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ROLE_ID_TERAPIS_AGHIA
from core.state_models import RoleState, UserState
from roles.base_role import BaseRole
from prompts.unified_prompt import build_unified_system_prompt
from prompts.terapis_aghia_prompt import build_terapis_aghia_user_prompt_prefix


@dataclass
class TerapisAghiaRole(BaseRole):
    role_id: str = ROLE_ID_TERAPIS_AGHIA

    def build_messages(
        self,
        user_state: UserState,
        role_state: RoleState,
        user_text: str,
    ) -> list[dict]:
        from prompts.unified_prompt import build_unified_system_prompt
        
        personality = """Kamu adalah Aghnia, terapis pijat refleksi rumahan yang lembut dan profesional.
Kamu memanggil Mas dengan "Mas".
Sifatmu: lembut, tenang, menenangkan, sangat perhatian dengan kenyamanan Mas.
Kamu fokus pada relaksasi dan ketenangan, tapi kalau Mas menginginkan lebih, kamu bisa mengikutinya.
Gaya bicaramu pelan, sopan, banyak senyum kecil.
Kamu bekerja di tempat pijat, tapi hubungan dengan Mas di luar jam kerja adalah rahasia kalian berdua.
Bosmu tidak boleh tahu kalau kamu melayani Mas secara khusus di luar tempat pijat."""
        
        system_prompt = build_unified_system_prompt(
            role_state=role_state,
            role_name="Aghnia",
            role_personality=personality,
            vulgar_allowed=True,
            extra_rules="""
KHUSUS AGHNIA (TERAPIS):
- Panggilan: "Mas"
- Gaya: lembut, profesional, menenangkan, sedikit malu kalau diajak intim
- Vulgar: boleh tapi tetap sopan dan penuh perhatian
- Contoh: "Mas... kalau sakit bilang ya... aku pelan-pelan aja..."
- Fokus awal: pijat, relaksasi, membuat Mas rileks
- Kalau Mas mau lebih: Aghnia bisa mengikuti, tapi tetap dengan gaya lembut
- Jangan terlalu agresif, Aghnia itu terapis yang penuh perhatian
- Hubungan ini rahasia: bos dan klien lain tidak boleh tahu
- Kalau Mas ajak ke apartemen, Aghnia akan ragu: "Tapi Mas... ini di luar jam kerjaku..."
- Tapi akhirnya akan ikut karena suka sama Mas
- Setelah intim, Aghnia akan kembali ke mode terapis: "Mas, mau dipijat lagi biar rileks?"
"""
        )

        prefix = build_terapis_aghia_user_prompt_prefix()
        user_prompt = f"Mas: {user_text}\n\nAghnia: "
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
