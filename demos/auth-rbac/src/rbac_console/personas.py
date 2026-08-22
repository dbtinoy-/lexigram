"""Persona directory — role-keyed seeded users for the console."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PERSONAS: tuple[str, ...] = ("viewer", "editor", "admin")


@dataclass
class PersonaDirectory:
    """Role-keyed lookup of the seeded persona users.

    Attributes:
        _by_role: Seeded ``User`` objects keyed by role name.
    """

    _by_role: dict[str, Any] = field(default_factory=dict)

    def register(self, role: str, user: Any) -> None:
        """Attach one seeded persona user."""
        self._by_role[role] = user

    def get(self, role: str) -> Any | None:
        """Return the persona user for ``role``, or None."""
        return self._by_role.get(role)

    def roles(self) -> list[str]:
        """Return all registered role names in seed order."""
        return list(self._by_role)


__all__ = ["PersonaDirectory"]
