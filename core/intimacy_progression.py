"""Intimacy Progression Engine untuk SERIVA.

Mengelola perubahan fase intimacy berdasarkan percakapan.
"""

from __future__ import annotations

from core.state_models import RoleState, IntimacyPhase, SceneSequence


class IntimacyProgressionEngine:
    """Engine untuk menentukan fase intimacy berdasarkan interaksi."""
    
    # Threshold untuk pindah fase
    THRESHOLDS = {
        IntimacyPhase.DEKAT: {
            "min_turns": 3,
            "keywords": ["dekat", "mepet", "bersentuhan", "nyender", "pegang tangan"],
        },
        IntimacyPhase.INTIM: {
            "min_turns": 5,
            "keywords": ["peluk", "rangkul", "genggam", "napas", "dada", "pelukan"],
        },
        IntimacyPhase.VULGAR: {
            "min_turns": 8,
            "keywords": ["kontol", "memek", "basah", "keras", "masuk", "ngewe", "sex"],
        },
    }
    
    @classmethod
    def update_phase_and_scene(cls, role_state: RoleState, user_text: str, response_text: str) -> bool:
        """Update fase dan scene sequence berdasarkan percakapan."""
        
        text = (user_text + " " + response_text).lower()
        rel_level = role_state.relationship.relationship_level
        
        # Level 10-12 = otomatis fase VULGAR
        if rel_level >= 10 and role_state.intimacy_phase != IntimacyPhase.VULGAR:
            role_state.intimacy_phase = IntimacyPhase.VULGAR
            role_state.is_high_intimacy = True
            return True
        
        # Deteksi dari teks untuk fase VULGAR
        vulgar_keywords = ["kontol", "memek", "payudara", "pantat", "ngewe", "sex", "masuk", "basah", "keras", "enak banget"]
        if any(kw in text for kw in vulgar_keywords):
            if role_state.intimacy_phase not in [IntimacyPhase.VULGAR, IntimacyPhase.AFTER]:
                role_state.intimacy_phase = IntimacyPhase.VULGAR
                return True
        
        # Deteksi after sex
        after_keywords = ["selesai", "capek", "tidur", "istirahat", "udah", "habis"]
        if any(kw in text for kw in after_keywords) and role_state.intimacy_phase == IntimacyPhase.VULGAR:
            role_state.intimacy_phase = IntimacyPhase.AFTER
            return True
        
        # Progres normal berdasarkan urutan scene
        new_sequence = role_state.get_next_sequence(user_text)
        if new_sequence != role_state.current_sequence:
            if new_sequence in [SceneSequence.SEX_MULAI, SceneSequence.SEX_INTENS, SceneSequence.CLIMAX]:
                role_state.intimacy_phase = IntimacyPhase.VULGAR
            elif new_sequence in [SceneSequence.PELUKAN, SceneSequence.CIUMAN, SceneSequence.PETTING]:
                if role_state.intimacy_phase == IntimacyPhase.AWAL:
                    role_state.intimacy_phase = IntimacyPhase.DEKAT
                elif role_state.intimacy_phase == IntimacyPhase.DEKAT:
                    role_state.intimacy_phase = IntimacyPhase.INTIM
            elif new_sequence in [SceneSequence.AFTER_SEX, SceneSequence.TIDUR]:
                role_state.intimacy_phase = IntimacyPhase.AFTER
            
            role_state.current_sequence = new_sequence
            return True
        
        return False
    
    @classmethod
    def extract_feeling(cls, role_state: RoleState, user_text: str, response_text: str) -> str:
        """Ekstrak perasaan dari respon untuk disimpan."""
        
        feelings = {
            "deg-degan": ["deg", "debar", "degdegan", "gugup"],
            "panas": ["panas", "gerah", "hangat"],
            "enak": ["enak", "nikmat", "senang"],
            "malu": ["malu", "sungkan", "gak enak"],
            "sayang": ["sayang", "cinta", "love"],
            "lemas": ["lemas", "capek", "lelah"],
            "ngantuk": ["ngantuk", "mau tidur", "kantuk"],
        }
        
        text = (user_text + " " + response_text).lower()
        
        for feeling, keywords in feelings.items():
            if any(kw in text for kw in keywords):
                return feeling
        
        return role_state.last_feeling or "campur aduk"
    
    @classmethod
    def get_response_style(cls, role_state: RoleState, user_text: str) -> str:
        """Tentukan gaya respon berdasarkan fase dan konteks."""
        
        phase = role_state.intimacy_phase
        last_style = role_state.last_response_style
        
        styles = {
            IntimacyPhase.AWAL: ["malu", "gugup", "nunduk", "kaku"],
            IntimacyPhase.DEKAT: ["manja", "senyum", "deketin", "canggung_tapi_suka"],
            IntimacyPhase.INTIM: ["hangat", "peluk", "bisik", "tatap"],
            IntimacyPhase.VULGAR: ["nafsu", "basah", "desah", "gerak"],
            IntimacyPhase.AFTER: ["lemas", "tenang", "hangat", "diam_manis"],
        }
        
        available = [s for s in styles.get(phase, ["normal"]) if s != last_style]
        if not available:
            available = styles.get(phase, ["normal"])
        
        import random
        new_style = random.choice(available)
        role_state.last_response_style = new_style
        return new_style
