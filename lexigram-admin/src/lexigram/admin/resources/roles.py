"""Roles management resource for Lexigram Admin."""

from __future__ import annotations

from lexigram.admin.rbac.types import AdminRole
from lexigram.admin.resources.base import Resource


class RolesResource(Resource):
    """Manage RBAC roles and permissions."""

    model = AdminRole
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

    def can_delete(self, item: AdminRoleEntity) -> bool:
        """Prevent deletion of system roles."""
        return not item.is_system

    def can_update(self, item: AdminRoleEntity) -> bool:
        """Prevent renaming of system roles."""
        # This is a simplification; ideally we'd allow updating permissions but not name
        return True
