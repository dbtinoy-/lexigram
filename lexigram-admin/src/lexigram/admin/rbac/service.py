"""Central permission service for enforcing RBAC rules."""

from __future__ import annotations

from typing import Any

from lexigram.admin.rbac.policies import get_policy
from lexigram.admin.rbac.schema import ResourcePermissions
from lexigram.admin.rbac.types import PolicyContext
from lexigram.contracts.core.di import ContainerResolverProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


from lexigram.contracts.auth import AuthorizerProtocol


@inject
class PermissionService:
    """Central service for all permission checks in Lexigram Admin.

    Delegates core RBAC logic to an implementation of AuthorizerProtocol.
    Maintains ResourcePermissions registry for admin UI.
    """

    def __init__(self, authorization_service: AuthorizerProtocol | None = None):
        self.authorization_service = authorization_service
        self._schemas: dict[str, ResourcePermissions] = {}

    def set_roles(self, roles: dict[str, Any]) -> None:
        """Delegate to unified service."""
        if self.authorization_service is None:
            logger.warning(
                "PermissionService: No authorizer configured; skipping set_roles"
            )
            return
        self.authorization_service.set_roles(roles)

    async def sync_from_db(self, container: ContainerResolverProtocol) -> None:
        """Delegate to unified service."""
        if self.authorization_service is None:
            logger.warning(
                "PermissionService: No authorizer configured; skipping sync_from_db"
            )
            return
        await self.authorization_service.sync_from_db(container)

    def register(self, resource_name: str, schema: ResourcePermissions) -> None:
        """Register permission schema for a resource."""
        self._schemas[resource_name] = schema
        logger.debug("Registered permissions for resource: %s", resource_name)

    def get_schema(self, resource_name: str) -> ResourcePermissions | None:
        """Get the permission schema for a resource."""
        return self._schemas.get(resource_name)

    # --- CRUD Operations ---

    async def can_list(self, user: Any, resource_name: str) -> bool:
        schema = self.get_schema(resource_name)
        return (
            await self._check_access(user, schema.can_list, resource_name, "list")
            if schema
            else True
        )

    async def can_view(self, user: Any, resource_name: str) -> bool:
        schema = self.get_schema(resource_name)
        return (
            await self._check_access(user, schema.can_view, resource_name, "view")
            if schema
            else True
        )

    async def can_create(self, user: Any, resource_name: str) -> bool:
        schema = self.get_schema(resource_name)
        return (
            await self._check_access(user, schema.can_create, resource_name, "create")
            if schema
            else True
        )

    async def can_edit(self, user: Any, resource_name: str, record: Any = None) -> bool:
        schema = self.get_schema(resource_name)
        if not schema:
            return True

        if not await self._check_access(user, schema.can_edit, resource_name, "edit"):
            return False

        # Apply RLS policy if record is provided
        if schema.rls_policy and record:
            policy = get_policy(schema.rls_policy)
            if policy:
                context = PolicyContext(user, resource_name, "edit", record)
                return policy(context)

        return True

    async def can_delete(
        self, user: Any, resource_name: str, record: Any = None
    ) -> bool:
        schema = self.get_schema(resource_name)
        if not schema:
            return True

        if not await self._check_access(
            user, schema.can_delete, resource_name, "delete"
        ):
            return False

        if schema.rls_policy and record:
            policy = get_policy(schema.rls_policy)
            if policy:
                context = PolicyContext(user, resource_name, "delete", record)
                return policy(context)

        return True

    # --- Field Level ---

    async def can_view_field(
        self, user: Any, resource_name: str, field_name: str
    ) -> bool:
        schema = self.get_schema(resource_name)
        if not schema or field_name not in schema.fields:
            return True
        return await self._check_access(user, schema.fields[field_name].view_roles)

    async def can_edit_field(
        self, user: Any, resource_name: str, field_name: str
    ) -> bool:
        schema = self.get_schema(resource_name)
        if not schema or field_name not in schema.fields:
            return True
        return await self._check_access(user, schema.fields[field_name].edit_roles)

    async def should_mask_field(
        self, user: Any, resource_name: str, field_name: str
    ) -> bool:
        schema = self.get_schema(resource_name)
        if not schema or field_name not in schema.fields:
            return False
        return await self._check_access(user, schema.fields[field_name].mask_for)

    # --- Actions ---

    async def can_perform_action(
        self,
        user: Any,
        resource_name: str,
        action_name: str,
    ) -> bool:
        schema = self.get_schema(resource_name)
        if not schema or action_name not in schema.actions:
            return True
        return await self._check_access(
            user,
            schema.actions[action_name].allowed_roles,
            resource_name,
            action_name,
        )

    # --- Internal Helpers ---

    async def _check_access(
        self,
        user: Any,
        allowed_roles: set[str],
        resource: str | None = None,
        action: str | None = None,
    ) -> bool:
        """Delegate to the unified authorizer."""
        if self.authorization_service:
            return await self.authorization_service.check_access(
                user,
                allowed_roles,
                resource,
                action,
            )
        # Fallback for legacy usage without a configured authorizer
        logger.warning("PermissionService: No authorizer configured; denying access")
        return False
