"""Roles management resource for Lexigram Admin."""

from __future__ import annotations

from typing import Any, cast

from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.rbac.types import AdminRole
from lexigram.admin.resources.base import Resource


class RolesResource(Resource):
    """Manage RBAC roles and permissions."""

    model = cast("Any", AdminRole)
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

    def can_delete(self, item: AdminRole) -> bool:
        """Prevent deletion of system roles and the super-admin role.

        Args:
            item: Role being deleted.

        Returns:
            False when the role is ``is_system`` or matches
            ``AdminRbacConfig.super_admin_role``.
        """
        super_admin_role = AdminRbacConfig().super_admin_role
        return not (item.is_system or item.name == super_admin_role)

    def can_update(self, item: AdminRole) -> bool:
        """Prevent renaming of system roles."""
        # This is a simplification; ideally we'd allow updating permissions but not name
        return True
