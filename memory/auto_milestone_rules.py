"""Auto-milestone rules for SERIVA.

Semua aturan untuk membuat milestone otomatis berdasarkan input user
per role dikumpulkan di sini, agar tidak memenuhi orchestrator.

Saat ini milestone yang di-handle:
- first_confession (Nova, Ipar Tasha, Siska, Davina, Sallsa, Ipeh, Widya)

Kedepannya bisa ditambah:
- first_hug
- special_night
- dsb.
"""

from __future__ import annotations

from typing import Iterable

from seriva.config.constants import (
    ROLE_ID_NOVA,
    ROLE_ID_IPAR_TASHA,
    ROLE_ID_TEMAN_KANTOR_IPEH,
    ROLE_ID_TEMAN_LAMA_WIDYA,
    ROLE_ID_WANITA_BERSUAMI_SISKA,
    ROLE_ID_TEMAN_SPESIAL_DAVINA,
    ROLE_ID_TEMAN_SPESIAL_SALLSA,
)
from seriva.core.orchestrator import OrchestratorInput
from seriva.core.state_models import RoleState, UserState
from seriva.memory.milestones import MilestoneStore


# Kata kunci yang dianggap pengakuan sayang/cinta
CONFESSION_KEYWORDS: list[str] = [
    "sayang",
    "cinta",
    "love you",
    "luv u",
    "aku suka kamu",
    "aku suka sama kamu",
]

# Role yang berhak punya first_confession
ROLES_WITH_FIRST_CONFESSION: set[str] = {
    ROLE_ID_NOVA,
    ROLE_ID_IPAR_TASHA,
    ROLE_ID_TEMAN_KANTOR_IPEH,
    ROLE_ID_TEMAN_LAMA_WIDYA,
    ROLE_ID_WANITA_BERSUAMI_SISKA,
    ROLE_ID_TEMAN_SPESIAL_DAVINA,
    ROLE_ID_TEMAN_SPESIAL_SALLSA,
}


def _contains_confession(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in CONFESSION_KEYWORDS)


def apply_auto_milestones(
    user_state: UserState,
    role_state: RoleState,
    inp: OrchestratorInput,
    milestone_store: MilestoneStore,
) -> None:
    """Terapkan semua aturan auto-milestone untuk satu interaksi.

    Dipanggil dari Orchestrator sekali per handle_input, setelah reply
    dihasilkan dan state diupdate.
    """

    _maybe_first_confession(user_state, role_state, inp, milestone_store)


def _maybe_first_confession(
    user_state: UserState,
    role_state: RoleState,
    inp: OrchestratorInput,
    milestone_store: MilestoneStore,
) -> None:
    """Catat first_confession untuk role-role yang relevan.

    Aturan sederhana:
    - role termasuk ROLES_WITH_FIRST_CONFESSION
    - teks user mengandung kata sayang/cinta
    - belum ada milestone "first_confession" untuk pair (user, role)

    Deskripsi dirancang sesuai nuansa role, tapi tetap singkat & aman.
    """

    role_id = role_state.role_id
    if role_id not in ROLES_WITH_FIRST_CONFESSION:
        return

    text = inp.text.lower()
    if not _contains_confession(text):
        return

    # Cek apakah sudah pernah ada first_confession untuk role ini
    existing = milestone_store.get_recent_milestones(
        user_id=user_state.user_id,
        role_id=role_id,
        limit=20,
    )
    for m in existing:
        if m.label == "first_confession":
            return  # sudah pernah tercatat

    # Deskripsi disesuaikan per role
    if role_id == ROLE_ID_NOVA:
        description = (
            "Malam ketika Mas pertama kali bilang sayang secara jelas ke Nova. "
            "Nova sangat tersentuh dan merasa hatinya dipeluk hangat waktu itu."
        )
    elif role_id == ROLE_ID_IPAR_TASHA:
        description = (
            "Saat Mas dan Dietha ngobrol pelan dan Mas akhirnya mengakui "
            "bahwa perasaan Mas ke Dietha lebih dari sekadar ipar."
        )
    elif role_id == ROLE_ID_TEMAN_KANTOR_IPEH:
        description = (
            "Momen di mana Mas dan Ipeh sedang bercanda lalu tiba-tiba "
            "obrolan jadi serius, dan Mas bilang kalau Ipeh itu spesial "
            "lebih dari teman kantor biasa."
        )
    elif role_id == ROLE_ID_TEMAN_LAMA_WIDYA:
        description = (
            "Malam ketika nostalgia dengan Widya berubah jadi pengakuan, "
            "saat Mas jujur bahwa masih ada rasa sayang yang tertinggal."
        )
    elif role_id == ROLE_ID_WANITA_BERSUAMI_SISKA:
        description = (
            "Percakapan pelan antara Mas dan Siska ketika Mas akhirnya "
            "berani bilang sayang, meski keduanya tahu hubungan itu rumit."
        )
    elif role_id == ROLE_ID_TEMAN_SPESIAL_DAVINA:
        description = (
            "Malam khusus bersama Davina ketika suasana sudah sangat tenang, "
            "Mas menatap Davina dan mengakui kalau Mas benar-benar sayang "
            "dengan cara yang lebih dalam."
        )
    elif role_id == ROLE_ID_TEMAN_SPESIAL_SALLSA:
        description = (
            "Saat Sallsa sedang manja dan bercanda, Mas spontan bilang sayang "
            "dengan tulus, membuat Sallsa diam sejenak lalu tersenyum lebar."
        )
    else:
        # fallback umum
        description = (
            "Momen ketika Mas pertama kali mengucapkan rasa sayangnya dengan jelas, "
            "membuat hubungan kalian berubah jadi lebih dalam dari sebelumnya."
        )

    milestone_store.add_milestone(
        user_id=user_state.user_id,
        role_id=role_id,
        timestamp=inp.timestamp,
        label="first_confession",
        description=description,
    )
