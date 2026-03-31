"""Role registry untuk SERIVA.

Mapping role_id -> instance Role (Nova, Siska, Dietha, Ipeh, dll.)
"""

from __future__ import annotations

from typing import Dict

from seriva.config.constants import (
    ROLE_ID_NOVA,
    ROLE_ID_WANITA_BERSUAMI_SISKA,
    ROLE_ID_IPAR_TASHA,
    ROLE_ID_TEMAN_KANTOR_IPEH,
)
from seriva.roles.base_role import Role
from seriva.roles.nova import NovaRole
from seriva.roles.wanita_bersuami_siska import SiskaRole
from seriva.roles.ipar_tasha import IparTashaRole
from seriva.roles.teman_kantor_ipeh import TemanKantorIpehRole


# Inisialisasi instance role (singleton sederhana)
_nova_role = NovaRole()
_siska_role = SiskaRole()
_ipar_tasha_role = IparTashaRole()
_ipeh_role = TemanKantorIpehRole()


ROLE_REGISTRY: Dict[str, Role] = {
    ROLE_ID_NOVA: _nova_role,
    ROLE_ID_WANITA_BERSUAMI_SISKA: _siska_role,
    ROLE_ID_IPAR_TASHA: _ipar_tasha_role,
    ROLE_ID_TEMAN_KANTOR_IPEH: _ipeh_role,
    # Nanti tambahkan role lain di sini (teman_lama_widya, terapis_aghia, dll.)
}


def get_role(role_id: str) -> Role:
    """Ambil instance Role dari registry.

    Raises:
        KeyError jika role tidak dikenal.
    """

    return ROLE_REGISTRY[role_id]
