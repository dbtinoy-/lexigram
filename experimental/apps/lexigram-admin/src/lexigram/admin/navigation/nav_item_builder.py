"""NavItemBuilder — builds sidebar navigation and system menu from registered resources."""

from __future__ import annotations

from typing import Any

from lexigram.admin.config import AdminConfig
from lexigram.logging import get_logger

_log = get_logger(__name__)


class NavItemBuilder:
    """Builds sidebar navigation items and system menu from registered resource instances.

    Registered as a singleton by AdminProvider. Populated with resolved
    resource instances by AdminProvider.mount_to_app() after the container
    has resolved all resource classes.

    Constructor injection only — no setters.
    """

    def __init__(
        self,
        config: AdminConfig,
        system_menu_items: list[dict[str, Any]] | None = None,
    ) -> None:
        self._config = config
        self._resolved_resources: dict[str, Any] = {}
        self._system_menu_items = system_menu_items or []

    def set_resources(self, resolved_resources: dict[str, Any]) -> None:
        """Populate with resolved resource instances.

        Called once by AdminProvider.mount_to_app() after the container
        resolves all registered resource classes. Not a setter injection — this
        is domain-data population that happens at a well-defined point in the
        application lifecycle.

        Args:
            resolved_resources: Mapping of resource name to resolved instance.
        """
        self._resolved_resources = resolved_resources

    def set_system_menu_items(self, items: list[dict[str, Any]]) -> None:
        """Set system menu items (shown in sidebar footer).

        Called by application code or bundle providers to populate the
        system/footer menu with links like Settings, Health, etc.

        Args:
            items: List of item dicts with ``label``, ``href``, and optional
                ``icon`` and ``render`` keys.
        """
        self._system_menu_items = list(items)

    def add_system_menu_item(self, item: dict[str, Any]) -> None:
        """Append a single item to the system menu.

        Args:
            item: Item dict with ``label``, ``href``, and optional
                ``icon`` and ``render`` keys.
        """
        self._system_menu_items.append(item)

    def build_nav_items(self, current_path: str | None = None) -> list[dict[str, Any]]:
        """Build sidebar navigation items from registered resources and nav groups.

        Args:
            current_path: Current request path for active-state detection.
                Items whose href matches the path (exact or sub-path) get
                ``active=True``.

        Returns:
            Flat list of dicts understood by ``AdminShell._prepare_navigation()``.
        """
        from lexigram.admin.config import AdminNavigationGroup  # noqa: F401

        prefix = self._config.prefix.rstrip("/")

        # Collect items per group from resolved resources
        group_items: dict[str, list[dict[str, Any]]] = {}
        for resource_name, resource_instance in self._resolved_resources.items():
            if not getattr(resource_instance, "visible_in_sidebar", True):
                continue
            group_key = getattr(resource_instance, "cluster", None) or "default"
            label = (
                getattr(resource_instance, "label", None)
                or resource_name.replace("_", " ").title()
            )
            icon = getattr(resource_instance, "icon", "box")
            href = f"{prefix}/{resource_name}"
            active = self._is_active(href, current_path)
            group_items.setdefault(group_key, []).append(
                {"label": label, "icon": icon, "href": href, "active": active}
            )

        # Build ordered flat nav list: group header then items
        nav_groups_cfg: dict[str, Any] = self._config.navigation_groups or {}
        result: list[dict[str, Any]] = []
        seen_groups: set[str] = set()

        # Emit groups that have config entries, sorted by order
        for group_key, group_cfg in sorted(
            nav_groups_cfg.items(), key=lambda kv: getattr(kv[1], "order", 999)
        ):
            items = group_items.get(group_key, [])
            if not items:
                continue
            seen_groups.add(group_key)
            result.append({"is_group": True, "label": group_cfg.label})
            result.extend(items)

        # Emit remaining groups that have no config entry
        for group_key, items in group_items.items():
            if group_key not in seen_groups:
                result.append(
                    {"is_group": True, "label": group_key.replace("_", " ").title()}
                )
                result.extend(items)

        return result

    def build_system_menu_items(self) -> list[dict[str, Any]]:
        """Build system-level menu items set by the application.

        Returns:
            List of item dicts for the system footer section.
        """
        return list(self._system_menu_items)

    @staticmethod
    def _is_active(href: str, current_path: str | None) -> bool:
        """Determine if a nav item should be highlighted as active."""
        if not current_path:
            return False
        return current_path == href or current_path.startswith(href + "/")


__all__ = ["NavItemBuilder"]
