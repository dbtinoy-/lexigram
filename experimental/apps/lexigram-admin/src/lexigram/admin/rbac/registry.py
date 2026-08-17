"""Global registry for permissions and roles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.admin.rbac.schema import ResourcePermissions

if TYPE_CHECKING:
    from lexigram.admin.rbac.service import PermissionService

_resource_registry: dict[str, ResourcePermissions] = {}


def register_resource_permissions(
    resource_name: str,
    permissions: ResourcePermissions,
    permission_service: PermissionService | None = None,
) -> None:
    """Register permissions for a resource.

    Args:
        resource_name: Name of the resource.
        permissions: Permission schema to register.
        permission_service: Injected :class:`~lexigram.admin.rbac.service.PermissionService`
            instance. When provided, the schema is also registered on the service.
    """
    _resource_registry[resource_name] = permissions
    if permission_service is not None:
        permission_service.register(resource_name, permissions)


def get_resource_permissions(resource_name: str) -> ResourcePermissions:
    """Get registered permissions for a resource."""
    return _resource_registry.get(resource_name, ResourcePermissions())
