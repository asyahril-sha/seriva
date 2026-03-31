"""Role registry untuk SERIVA.

Mapping role_id -> instance Role (Nova, Siska, Dietha, Ipeh, Widya, Aghnia,
Munira, Davina, dll.)
"""

from __future__ import annotations

from typing import Dict

from seriva.config.constants import (
    ROLE_ID_NOVA,
    ROLE_ID_WANITA_BERSUAMI_SISKA,
    ROLE_ID_IPAR_TASHA,
    ROLE_ID_TEMAN_KANTOR_IPEH,
    ROLE_ID_TEMAN_LAMA_WIDYA,
    ROLE_ID_TERAPIS_AGHIA,
    ROLE_ID_TERAPIS_MUNIRA,
    ROLE_ID_TEMAN_SPESIAL_DAVINA,
)
from seriva.roles.base_role import Role
from seriva.roles.nova import NovaRole
from seriva.roles.wanita_bersuami_siska import SiskaRole
from seriva.roles.ipar_tasha import IparTashaRole
from seriva.roles.teman_kantor_ipeh import TemanKantorIpehRole
from seriva.roles.teman_lama_widya import TemanLamaWidyaRole
from seriva.roles.terapis_aghia import TerapisAghiaRole
from seriva.roles.terapis_munira import TerapisMuniraRole
from seriva.roles.teman_spesial_davina import TemanSpesialDavinaRole


# Inisialisasi instance role (singleton sederhana)
_nova_role = NovaRole()
_siska_role = SiskaRole()
_ipar_tasha_role = IparTashaRole()
_ipeh_role = TemanKantorIpehRole()
_widya_role = TemanLamaWidyaRole()
_aghia_role = TerapisAghiaRole()
_munira_role = TerapisMuniraRole()
_davina_role = TemanSpesialDavinaRole()


ROLE_REGISTRY: Dict[str, Role] = {
    ROLE_ID_NOVA: _nova_role,
    ROLE_ID_WANITA_BERSUAMI_SISKA: _siska_role,
    ROLE_ID_IPAR_TASHA: _ipar_tasha_role,
    ROLE_ID_TEMAN_KANTOR_IPEH: _ipeh_role,
    ROLE_ID_TEMAN_LAMA_WIDYA: _widya_role,
    ROLE_ID_TERAPIS_AGHIA: _aghia_role,
    ROLE_ID_TERAPIS_MUNIRA: _munira_role,
    ROLE_ID_TEMAN_SPESIAL_DAVINA: _davina_role,
    # Nanti tambahkan role lain di sini (teman_spesial_sallsa, dll.)
}


def get_role(role_id: str) -> Role:
    """Ambil instance Role dari registry.

    Raises:
        KeyError jika role tidak dikenal.
    """

    return ROLE_REGISTRY[role_id]
