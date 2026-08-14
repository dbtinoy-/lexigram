"""Permission inventory for the RBAC admin UI.

The form pages render grouped checkboxes from an inventory of
``resource.action`` strings.  Supply the builtin resources set
(``roles``, ``users``, ``settings``) plus any resources discovered from
the bundle provider's registered resource classes.  The service is
mutable and registered as a container singleton so discovery can
populate it at mount time; the controller reads ``options()`` on every
request, so late registrations appear immediately.
"""

from __future__ import annotations

from collections.abc import Iterable

_RBAC_RESOURCES: tuple[str, ...] = ("roles", "users", "settings")
_RBAC_ACTIONS: tuple[str, ...] = (
    "list",
    "view",
    "create",
    "update",
    "delete",
    "export",
)


class PermissionInventoryService:
    """Mutable permission inventory for the RBAC editing pages."""

    def __init__(self) -> None:
        """Initialise with the builtin resources only."""
        self._resources: list[str] = list(_RBAC_RESOURCES)

    def register_resources(self, names: Iterable[str]) -> None:
        """Append unknown, non-blank resource names (case normalized).

        Duplicates and blank entries are ignored.

        Args:
            names: Resource names to add to the inventory.
        """
        for name in names:
            key = str(name).strip().lower()
            if key and key not in self._resources:
                self._resources.append(key)

    def resources(self) -> tuple[str, ...]:
        """Return the current resource names, builtin first."""
        return tuple(self._resources)

    def options(self) -> dict[str, list[str]]:
        """Return grouped permission options for every resource.

        Returns:
            Mapping ``{resource: ["resource.action", ...]}`` with all
            builtin actions per resource.
        """
        return {
            resource: [f"{resource}.{action}" for action in _RBAC_ACTIONS]
            for resource in self._resources
        }


__all__ = [
    "_RBAC_ACTIONS",
    "_RBAC_RESOURCES",
    "PermissionInventoryService",
]
