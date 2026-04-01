"""Base role class untuk semua role SERIVA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.state_models import RoleState, UserState


class Role(Protocol):  # pragma: no cover - interface
    role_id: str

    def build_messages(self, user_state: UserState, role_state: RoleState, user_text: str) -> list[dict]:
        """Bangun daftar messages untuk dikirim ke LLM."""
        ...


@dataclass
class BaseRole:
    """Implementasi dasar yang bisa dipakai role-role lain."""

    role_id: str

    def build_messages(self, user_state: UserState, role_state: RoleState, user_text: str) -> list[dict]:  # pragma: no cover - override di subclass
        raise NotImplementedError
