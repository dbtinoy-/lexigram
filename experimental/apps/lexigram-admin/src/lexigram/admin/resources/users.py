"""
User resource definition for Lexigram Admin.

This module defines the UserResource class that provides admin interface
for managing users with date range filtering capabilities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, cast

from lexigram.admin.actions import (
    CreateAction,
    DeleteAction,
    EditAction,
    ImpersonateAction,
    PermissionsAction,
)
from lexigram.admin.auth.entity import AdminUserEntity
from lexigram.admin.resources.base import Resource
from lexigram.admin.schema import BooleanField, DateField, SelectField, TextField
from lexigram.admin.ui.filters import SelectFilter, ToggleFilter
from lexigram.ui import BadgeColumn, DateColumn, TextColumn

if TYPE_CHECKING:
    from lexigram.admin.rbac.inventory import PermissionInventoryService


class UserResource(Resource):
    """
    Admin resource for managing users.

    Provides comprehensive user management with filtering by registration date
    and last active date using DateRangeFilter.
    """

    model = cast("Any", AdminUserEntity)
    name = "users"
    label = "Users"
    icon = "users"
    category = "system"
    service = None  # Will be set by DI or registry
    permission_inventory: PermissionInventoryService | None = None
    """Grouped RBAC permission inventory; wired at mount time for the
    per-user permission editor."""
    # Secret/framework-managed columns must never render in generated forms
    form_exclude_fields = (
        "id",
        "created_at",
        "updated_at",
        "hashed_password",
    )

    # UI Configuration
    layout_type = "sidebar"
    data_view = "tabular"

    # New SchemaField declarations (canonical definition)
    fields: list[Any] = [
        TextField(name="name", sortable=True, searchable=True),
        TextField(name="email", sortable=True, searchable=True),
        SelectField(
            name="role",
            options=[
                ("admin", "Admin"),
                ("moderator", "Moderator"),
                ("user", "User"),
                ("guest", "Guest"),
            ],
        ),
        SelectField(
            name="status",
            options=[
                ("active", "Active"),
                ("inactive", "Inactive"),
                ("pending", "Pending"),
                ("suspended", "Suspended"),
            ],
        ),
        DateField(name="created_at", label="Registration Date", sortable=True),
        DateField(name="last_active", sortable=True),
        BooleanField(name="is_active", label="Active"),
    ]

    # Columns configuration (legacy — kept for backward compat)
    columns: list[Any] = [
        TextColumn("name").sortable().searchable().weight("semibold"),
        TextColumn("email").sortable().searchable().copyable().color("blue"),
        BadgeColumn(
            "role",
            colors={
                "admin": "purple",
                "moderator": "blue",
                "user": "gray",
                "guest": "slate",
            },
        ),
        BadgeColumn(
            "status",
            colors={
                "active": "green",
                "inactive": "red",
                "pending": "yellow",
                "suspended": "orange",
            },
        ),
        DateColumn("created_at", label="Registration Date").datetime().sortable(),
        DateColumn("last_active").datetime().sortable(),
    ]

    # Filter configuration
    @property
    def filter_options(self) -> dict[str, Any]:
        """Define filter options for the user resource."""
        field_map: dict[str, Any] = {f.name: f for f in self.fields}
        return {
            "role": SelectFilter(
                "role",
                options=[v for v, _ in field_map["role"].options],
                label="Role",
            ),
            "status": SelectFilter(
                "status",
                options=[v for v, _ in field_map["status"].options],
                label="Status",
            ),
            "is_active": ToggleFilter("is_active", label="Active"),
        }

    # Actions configuration
    actions: list[Any] = [
        EditAction(),
        DeleteAction(),
        PermissionsAction(),
        ImpersonateAction(),
    ]

    # Header actions
    header_actions: list[Any] = [
        CreateAction(label="Add User"),
    ]

    # Search configuration
    search_fields = ["name", "email"]

    # Bulk actions
    bulk_actions: list[Any] = ["delete_selected", "export_csv"]

    # Permissions
    #
    # Checks go through has_role(), the one method common to every user
    # type reaching this resource. AdminUserRecord (admin.auth.user) has
    # roles: list[str] and has_role() but no is_admin, while AdminUser
    # (admin.auth.integration) exposes is_admin and delegates has_role()
    # to a wrapped framework user. Neither has a singular `role`.
    #
    # These previously read `user.is_admin or user.role in [...]`, which
    # raised AttributeError for both types. The caller in resources/
    # handler.py catches everything and fails closed, so the symptom was
    # every authenticated user getting 403 on /admin/users, with the real
    # cause only visible in the admin.resource_permission_check_failed log.
    _MANAGE_ROLES: ClassVar[tuple[str, ...]] = ("admin", "moderator")

    def has_view_permission(self, user: Any) -> bool:
        """Check if user can view users."""
        return self._has_any_role(user, self._MANAGE_ROLES)

    def has_add_permission(self, user: Any) -> bool:
        """Check if user can add users."""
        return self._has_any_role(user, ("admin",))

    def has_change_permission(self, user: Any) -> bool:
        """Check if user can change users."""
        return self._has_any_role(user, self._MANAGE_ROLES)

    def has_delete_permission(self, user: Any) -> bool:
        """Check if user can delete users."""
        return self._has_any_role(user, ("admin",))

    @staticmethod
    def _has_any_role(user: Any, roles: tuple[str, ...]) -> bool:
        """Return True when ``user`` holds any of ``roles``.

        Returns a real bool rather than the user object: these feed an
        ``if not allowed`` check, and returning None for an anonymous user
        would make the contract depend on truthiness.
        """
        if user is None:
            return False
        has_role = getattr(user, "has_role", None)
        if callable(has_role):
            return any(bool(has_role(role)) for role in roles)
        # Fall back to the roles list for user types that satisfy the
        # protocol's attribute but not its method.
        user_roles = getattr(user, "roles", ())
        return any(role in user_roles for role in roles)

    # Custom methods
    async def get_queryset(self, request: Any) -> Any:
        """Get the base queryset for users."""
        if self.service:
            return await self.service.list()
        return []

    async def get_object(self, pk: Any) -> Any:
        """Get a single user object."""
        if self.service:
            return await self.service.get_by_id(pk)
        return None

    async def create_object(self, data: dict[str, Any]) -> Any:
        """Create a new user."""
        if self.service:
            return await self.service.create(data)
        return None

    async def update_object(self, pk: Any, data: dict[str, Any]) -> Any:
        """Update an existing user."""
        if self.service:
            return await self.service.update(pk, data)
        return None

    async def delete_object(self, pk: Any) -> bool:
        """Delete a user."""
        if self.service:
            return await self.service.delete(pk)
        return False
