"""Protocols for the RBAC admin subsystem (roles management)."""

from __future__ import annotations

from typing import Protocol

from lexigram.admin.rbac.errors import (
    AdminRoleError,
    RoleDuplicateError,
    RoleNotFoundError,
    SystemRoleError,
)
from lexigram.contracts.auth import RoleDefinition
from lexigram.result import Result


class AdminRoleStoreProtocol(Protocol):
    """Persistence for admin roles (``admin_roles`` table)."""

    async def ensure_schema(self) -> None:
        """Create the roles table if it does not exist (idempotent)."""
        ...

    async def list_roles(self) -> list[RoleDefinition]:
        """Return all roles ordered by name."""
        ...

    async def get_role(self, name: str) -> RoleDefinition | None:
        """Return one role by name, or ``None`` when missing."""
        ...

    async def create_role(self, role: RoleDefinition) -> None:
        """Insert a new role. Raises on duplicate name."""
        ...

    async def update_role(self, role: RoleDefinition) -> None:
        """Update an existing role by name."""
        ...

    async def delete_role(self, name: str) -> bool:
        """Delete a role by name; ``True`` when a row was removed."""
        ...


class AdminRoleServiceProtocol(Protocol):
    """Role CRUD orchestration with authorization-sync and audit."""

    async def list_roles(self) -> list[RoleDefinition]:
        """Return all roles ordered by name."""
        ...

    async def create_role(
        self,
        name: str,
        description: str,
        permissions: list[str],
        inherits: list[str],
    ) -> Result[RoleDefinition, RoleDuplicateError | AdminRoleError]:
        """Create a role and mirror it into the authorizer."""
        ...

    async def update_role(
        self,
        name: str,
        description: str,
        permissions: list[str],
        inherits: list[str],
    ) -> Result[RoleDefinition, RoleNotFoundError | SystemRoleError | AdminRoleError]:
        """Update a role (system roles may not be renamed)."""
        ...

    async def delete_role(
        self, name: str
    ) -> Result[None, RoleNotFoundError | SystemRoleError | AdminRoleError]:
        """Delete a role (system roles may not be deleted)."""
        ...


__all__ = [
    "AdminRoleServiceProtocol",
    "AdminRoleStoreProtocol",
]
