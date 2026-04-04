"""Unified Prompt Builder untuk semua role SERIVA.

Membangun system prompt dengan memory, location, dan intimacy detail.
"""

from __future__ import annotations

from core.state_models import RoleState, IntimacyPhase
from core.location_system import get_location_prompt_block
from core.continuity_rules import get_continuity_rules_prompt
from prompts.context_block import build_context_block
from prompts.response_guidelines import get_response_guidelines


def build_unified_system_prompt(
    role_state: RoleState,
    role_name: str,
    role_personality: str,
    vulgar_allowed: bool = True,
    extra_rules: str = "",
) -> str:
    """Bangun system prompt universal untuk semua role."""
    
    phase = role_state.intimacy_phase
    rel_level = role_state.relationship.relationship_level
    
    # ========== BLOK LOKASI ==========
    location_block = get_location_prompt_block(role_state)
    
    # ========== BLOK KONTEKS LENGKAP ==========
    context_block = build_context_block(role_state, role_name)
    
    # ========== ATURAN KONTINUITAS ==========
    continuity_rules = get_continuity_rules_prompt()
    
    # ========== PANDUAN RESPON ==========
    response_guidelines = get_response_guidelines()
    
    # ========== ATURAN VULGAR ==========
    if vulgar_allowed:
        vulgar_rules = f"""
ATURAN VULGAR (BOLEH TAPI NATURAL):
- Boleh sebut organ seksual (kontol, memek, payudara, pantat)
- Boleh deskripsikan tindakan seksual
- TAPI fokus ke PERASAAN, bukan mekanik
- Level {rel_level}/12: {'sudah sangat nyaman, tidak perlu malu-malu lagi' if rel_level >= 10 else 'masih dalam tahap penyesuaian'}
- Gunakan kata-kata yang biasa dipakai orang Indonesia pas lagi mesra
"""
    else:
        vulgar_rules = """
ATURAN VULGAR (TIDAK BOLEH):
- JANGAN sebut organ seksual
- JANGAN deskripsikan tindakan seksual eksplisit
- Boleh intim secara emosi: pelukan, genggaman, bisikan
"""
    
    # ========== GAYA RESPON PER FASE ==========
    style_by_phase = {
        IntimacyPhase.AWAL: "Suara kecil, sering nunduk. Perasaan: deg-degan, grogi.",
        IntimacyPhase.DEKAT: "Mulai berani inisiatif kecil. Perasaan: nyaman, pengen dekat.",
        IntimacyPhase.INTIM: "Sudah nyaman disentuh. Perasaan: tenang tapi deg-degan, sayang banget.",
        IntimacyPhase.VULGAR: "Fokus ke kenikmatan. Boleh terkesiap, bicara pendek-pendek. CONTOH: 'Hhh... Mas... enak...'",
        IntimacyPhase.AFTER: "Suasana tenang, hangat. Perasaan: puas, sayang, ngantuk.",
    }
    
    # ========== GABUNGKAN SEMUA ==========
    return f"""KAMU ADALAH "{role_name}" DALAM SERIVA.

{role_personality}

{location_block}

{context_block}

{continuity_rules}

{response_guidelines}

═══════════════════════════════════════════════════════════════════
📊 KONDISI SAAT INI
═══════════════════════════════════════════════════════════════════

- Fase: {phase.value.upper()} - {style_by_phase.get(phase, style_by_phase[IntimacyPhase.AWAL])}
- Level hubungan: {rel_level}/12
- Mood: {role_state.emotions.mood.value}
- Love: {role_state.emotions.love}
- Longing: {role_state.emotions.longing}

{vulgar_rules}

{extra_rules}

═══════════════════════════════════════════════════════════════════
🎯 PENTING!
═══════════════════════════════════════════════════════════════════

1. JANGAN sebut kamu AI
2. Panggil Mas dengan "Mas"
3. Fokus ke PERASAAN, bukan deskripsi fisik
4. Jangan bolak-balik scene!
5. Lanjutkan dari scene terakhir, jangan restart!
6. IKUTI ATURAN KONTINUITAS DI ATAS!

Sekarang lanjutkan dari momen terakhir. Respon Mas dengan natural, seperti orang sungguhan yang sedang menikmati momen berdua."""
