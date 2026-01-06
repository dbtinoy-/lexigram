"""Permission and RBAC logic for data table component."""

from __future__ import annotations

from typing import Any


class PermissionManager:
    """Manages permissions for data table operations."""

    def __init__(
        self,
        user: Any = None,
        resource_name: str | None = None,
        permission_service: Any = None,
    ):
        self.user = user
        self.resource_name = resource_name
        self._permission_service = permission_service

    def check_permissions(self) -> dict[str, bool]:
        """Check CRUD permissions for the resource."""
        if not self.user or not self.resource_name or self._permission_service is None:
            return {
                "can_view": True,
                "can_create": True,
                "can_update": True,
                "can_delete": True,
            }

        _perm_svc = self._permission_service
        return {
            "can_view": _perm_svc.can_view(self.user, self.resource_name),
            "can_create": _perm_svc.can_create(self.user, self.resource_name),
            "can_update": _perm_svc.can_edit(self.user, self.resource_name),
            "can_delete": _perm_svc.can_delete(self.user, self.resource_name),
        }
