"""Role registry untuk SERIVA.

Mapping role_id -> instance Role (Nova, Siska, dll.)
"""

from __future__ import annotations

from typing import Dict

from seriva.config.constants import (
    ROLE_ID_NOVA,
    ROLE_ID_WANITA_BERSUAMI_SISKA,
)
from seriva.roles.base_role import Role
from seriva.roles.nova import NovaRole
from seriva.roles.wanita_bersuami_siska import SiskaRole


# Inisialisasi instance role (singleton sederhana)
_nova_role = NovaRole()
_siska_role = SiskaRole()


ROLE_REGISTRY: Dict[str, Role] = {
    ROLE_ID_NOVA: _nova_role,
    ROLE_ID_WANITA_BERSUAMI_SISKA: _siska_role,
    # Nanti tambahkan role lain di sini (ipar_tasha, teman_kantor_ipeh, dll.)
}


def get_role(role_id: str) -> Role:
    """Ambil instance Role dari registry.

    Raises:
        KeyError jika role tidak dikenal.
    """

    return ROLE_REGISTRY[role_id]
