"""Role management orchestrator for the RBAC admin UI.

Persists roles through ``AdminRoleStoreProtocol`` and mirrors every
mutation into the in-memory ``AuthorizationService`` so runtime access
checks reflect edits immediately.  System roles may have their
permissions changed but can never be renamed or deleted.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.rbac.errors import (
    AdminRoleError,
    RoleDuplicateError,
    RoleNotFoundError,
    SystemRoleError,
)
from lexigram.admin.rbac.types import AdminRole
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


@inject
class AdminRoleService:
    """Role CRUD with authorization-sync and audit (see module docstring).

    Args:
        role_store: Role persistence (``admin_roles`` table).
        authorization_service: Optional authorizer to mirror role changes
            into; ``None`` skips the mirror (fail open).
        audit_service: Optional audit logger; ``None`` skips auditing.
    """

    def __init__(
        self,
        role_store: Any,
        authorization_service: Any | None = None,
        audit_service: Any | None = None,
    ) -> None:
        self._role_store = role_store
        self._authorization_service = authorization_service
        self._audit_service = audit_service

    async def list_roles(self) -> list[AdminRole]:
        """Return all roles ordered by name (see protocol docs)."""
        return await self._role_store.list_roles()

    async def create_role(
        self,
        name: str,
        description: str,
        permissions: list[str],
        inherits: list[str],
    ) -> Result[AdminRole, RoleDuplicateError | AdminRoleError]:
        """Create a role, mirror it, and audit (see protocol docs)."""
        name = name.strip()
        existing = await self._role_store.get_role(name)
        if existing is not None:
            return Err(RoleDuplicateError(f"Role '{name}' already exists."))
        if not name:
            return Err(AdminRoleError("Role name is required."))

        role = AdminRole(
            name=name,
            description=description.strip(),
            permissions=sorted(set(permissions)),
            inherits=sorted(set(inherits)),
            is_system=False,
        )
        await self._role_store.create_role(role)
        self._mirror(role)
        await self._audit(AdminSecurityEventType.ROLE_CREATED, {"role": name})
        logger.info("admin.role_created", role=name)
        return Ok(role)

    async def update_role(
        self,
        name: str,
        description: str,
        permissions: list[str],
        inherits: list[str],
    ) -> Result[AdminRole, RoleNotFoundError | SystemRoleError | AdminRoleError]:
        """Update a role; system roles keep their name (see protocol docs)."""
        name = name.strip()
        role = await self._role_store.get_role(name)
        if role is None:
            return Err(RoleNotFoundError(f"Role '{name}' does not exist."))
        if role.is_system and name != role.name:
            return Err(SystemRoleError("System role names cannot be changed."))

        updated = AdminRole(
            name=role.name,
            description=description.strip(),
            permissions=sorted(set(permissions)),
            inherits=sorted(set(inherits)),
            is_system=role.is_system,
        )
        await self._role_store.update_role(updated)
        self._mirror(updated)
        await self._audit(AdminSecurityEventType.ROLE_UPDATED, {"role": name})
        logger.info("admin.role_updated", role=name)
        return Ok(updated)

    async def delete_role(
        self, name: str
    ) -> Result[None, RoleNotFoundError | SystemRoleError | AdminRoleError]:
        """Delete a role; system roles are protected (see protocol docs)."""
        name = name.strip()
        role = await self._role_store.get_role(name)
        if role is None:
            return Err(RoleNotFoundError(f"Role '{name}' does not exist."))
        if role.is_system:
            return Err(SystemRoleError("System roles cannot be deleted."))

        await self._role_store.delete_role(name)
        self._unmirror(name)
        await self._audit(AdminSecurityEventType.ROLE_DELETED, {"role": name})
        logger.info("admin.role_deleted", role=name)
        return Ok(None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mirror(self, role: AdminRole) -> None:
        """Push a role into the in-memory authorizer if available."""
        if self._authorization_service is None:
            return
        register = getattr(self._authorization_service, "register_role", None)
        if register is None:
            return
        register(
            role.name,
            {
                "description": role.description,
                "permissions": role.permissions,
                "inherits": role.inherits,
            },
        )

    def _unmirror(self, name: str) -> None:
        """Remove a role from the in-memory authorizer if available."""
        if self._authorization_service is None:
            return
        remove = getattr(self._authorization_service, "remove_role", None)
        if remove is not None:
            remove(name)

    async def _audit(self, event_type: AdminSecurityEventType, metadata: dict) -> None:
        """Fire an audit event when an audit service is bound."""
        if self._audit_service is None:
            return
        await self._audit_service.log_event(
            event_type=event_type,
            ip_address="",
            user_agent="",
            success=True,
            metadata=metadata,
        )


__all__ = ["AdminRoleService"]
