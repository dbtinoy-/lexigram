"""Global registry for permissions and roles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.admin.rbac.schema import ResourcePermissions
from lexigram.primitives.registry import Registry

if TYPE_CHECKING:
    from lexigram.admin.rbac.service import PermissionService


class ResourcePermissionRegistry(Registry[str, ResourcePermissions]):
    """Registry of per-resource permission schemas.

    Plugin-style registry (no built-in set): permissions are registered
    explicitly by resource providers at boot time.  Missing lookups return
    an empty :class:`ResourcePermissions` for fail-open defaults.
    """

    def __init__(self) -> None:
        """Create an empty resource-permission registry."""
        super().__init__(
            name="admin.rbac.resource_permissions",
            allow_overwrite=True,
        )


#: Module-level registry instance.
_resource_registry = ResourcePermissionRegistry()


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
    _resource_registry.register(resource_name, permissions)
    if permission_service is not None:
        permission_service.register(resource_name, permissions)


def get_resource_permissions(resource_name: str) -> ResourcePermissions:
    """Get registered permissions for a resource."""
    permissions = _resource_registry.get(resource_name)
    if permissions is None:
        return ResourcePermissions()
    return permissions
