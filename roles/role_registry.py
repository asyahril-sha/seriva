"""Role registry untuk SERIVA.

Mapping role_id -> instance Role (Nova, Ipar, dll.)
"""

from __future__ import annotations

from typing import Dict

from seriva.config.constants import ROLE_ID_NOVA
from seriva.roles.base_role import Role
from seriva.roles.nova import NovaRole


# Inisialisasi instance role (singleton sederhana)
_nova_role = NovaRole()


ROLE_REGISTRY: Dict[str, Role] = {
    ROLE_ID_NOVA: _nova_role,
    # Nanti tambahkan role lain di sini
}


def get_role(role_id: str) -> Role:
    """Ambil instance Role dari registry.

    Raises:
        KeyError jika role tidak dikenal.
    """

    return ROLE_REGISTRY[role_id]
