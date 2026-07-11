"""Roles management resource for Lexigram Admin."""

from __future__ import annotations

from typing import Any, cast

from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.resources.base import Resource
from lexigram.contracts.auth import RoleDefinition


class RolesResource(Resource):
    """Manage RBAC roles and permissions."""

    model = cast("Any", RoleDefinition)
    name = "roles"
    label = "Roles"
    icon = "shield-check"
    category = "system"

    # Fields to display in forms
    fields = [
        "name",
        "description",
        "permissions",
        "inherits",
        "is_system",
    ]

    # Fields to display in list view
    list_display = [
        "name",
        "description",
        "permissions",
        "inherits",
        "is_system",
    ]

    # SearchableProtocol fields
    search_fields = ["name", "description"]

    # Read-only fields (ensure system roles cannot be renamed easily)
    readonly_fields = ["created_at", "updated_at"]

    def __init__(self, rbac_config: AdminRbacConfig | None = None) -> None:
        """Store the resolved RBAC config for protected-role checks.

        Args:
            rbac_config: Optional; falls back to a default
                ``AdminRbacConfig`` (``super_admin_role="superadmin"``).
        """
        self._rbac_config = rbac_config or AdminRbacConfig()

    def can_delete(self, item: RoleDefinition) -> bool:
        """Prevent deletion of system roles and the super-admin role.

        Args:
            item: Role being deleted.

        Returns:
            False when the role is ``is_system`` or matches the
            configured ``super_admin_role``.
        """
        super_admin_role = self._rbac_config.super_admin_role
        return not (item.is_system or item.name == super_admin_role)

    def can_update(self, item: RoleDefinition) -> bool:
        """Prevent renaming or is_system-flag changes on protected roles.

        Args:
            item: Role being updated.

        Returns:
            False when the role is ``is_system`` or matches the
            configured ``super_admin_role``.
        """
        super_admin_role = self._rbac_config.super_admin_role
        return not (item.is_system or item.name == super_admin_role)
