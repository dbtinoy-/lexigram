"""Per-request navigation mount for the admin shell.

:class:`NavigationManager` is the single per-request entry point for
navigation state: it resolves the primary nav (resource items + assembler
contributions with dedup and per-request active state), the cluster
secondary sidebar for the active cluster center, and the user-menu entries
(cluster landings + settings/plugins) as :class:`MenuItem` values.

Everything is derived from request-scoped app state, so a fresh manager is
built per request — the mount lifecycle.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.clusters import ClusterRegistry
from lexigram.admin.navigation.types import MenuItem
from lexigram.admin.resources.urls import (
    DEFAULT_ADMIN_PREFIX,
    admin_prefix_from_request,
    mount_admin_url,
)

__all__ = ["NavigationManager"]


def _menu_entry(
    label: str,
    prefix: str,
    suffix: str,
    icon: str,
) -> MenuItem:
    """Build a user-menu entry under the configured admin prefix."""
    base = (prefix or DEFAULT_ADMIN_PREFIX).rstrip("/")
    href = f"{base}/{suffix.lstrip('/')}"
    return MenuItem(label=label, href=href, icon=icon)


class NavigationManager:
    """Per-request navigation state for the admin panel.

    Example:
        ```python
        nav_items, system_items, cluster_nav = NavigationManager(
            request
        ).resolve_nav()
        menu = NavigationManager(request).user_menu_items()
        ```
    """

    def __init__(self, request: Any) -> None:
        """Read app state relevant to navigation from the request.

        Args:
            request: Current Starlette request (its app carries the admin
                state: nav builder, assembler groups, cluster registry).
        """
        self._request = request
        self._admin_prefix = admin_prefix_from_request(request)
        state = getattr(request, "app", None) if request else None
        self._state = getattr(state, "state", None) if state else None
        self._nav_builder = (
            getattr(self._state, "nav_builder", None) if self._state else None
        )
        self._assembler_nav_items: list[dict] = (
            list(getattr(self._state, "assembler_nav_items", None) or [])
            if self._state
            else []
        )
        self._assembler_groups: dict[str, Any] | None = (
            getattr(self._state, "assembler_groups", None) or None
            if self._state
            else None
        )
        registry = (
            getattr(self._state, "cluster_registry", None) if self._state else None
        )
        self._cluster_registry = registry or ClusterRegistry.with_defaults()

    # ------------------------------------------------------------------
    # Clusters
    # ------------------------------------------------------------------

    def clusters(self) -> list[Any]:
        """Return all registered clusters in registry order.

        Returns:
            List of :class:`~lexigram.admin.clusters.Cluster` instances.
        """
        return self._cluster_registry.all()

    def active_cluster(self) -> Any | None:
        """Return the cluster whose center the current path belongs to.

        Returns:
            The matching cluster, or ``None`` outside every cluster center.
        """
        path = self._current_path()
        return self._cluster_registry.for_path(path, self._admin_prefix)

    def _current_path(self) -> str | None:
        if not self._request or not hasattr(self._request, "url"):
            return None
        return str(self._request.url.path)

    # ------------------------------------------------------------------
    # Primary nav resolution
    # ------------------------------------------------------------------

    def resolve_nav(self) -> tuple[list, list, list | None]:
        """Resolve the full navigation state for this request.

        Merges NavItemBuilder resource items with NavigationAssembler
        contributor items, computes per-request active states, collapses
        every cluster group from the primary sidebar, and — when the path
        belongs to a cluster center — returns its secondary nav.

        Returns:
            A tuple of (nav_items, system_menu_items, secondary_nav).
        """
        if self._nav_builder is None:
            return [], [], None

        from lexigram.admin.navigation.clusters import (
            build_secondary_nav,
            cluster_items,
            collapse_cluster_in_primary,
            is_cluster_path,
        )

        current_path = self._current_path()
        assembler_nav_items = []
        for raw_item in self._assembler_nav_items:
            if not isinstance(raw_item, dict):
                assembler_nav_items.append(raw_item)
                continue
            item = dict(raw_item)
            if item.get("href"):
                item["href"] = mount_admin_url(str(item["href"]), self._admin_prefix)
            if item.get("badge"):
                item["badge"] = mount_admin_url(str(item["badge"]), self._admin_prefix)
            assembler_nav_items.append(item)

        cluster_nav: list | None = None
        items_by_cluster: dict[Any, list] = {}
        for cluster in self._cluster_registry.all():
            items = cluster_items(self._assembler_groups, cluster=cluster)
            if not items:
                continue
            items_by_cluster[cluster] = items
            if cluster_nav is None and is_cluster_path(
                current_path,
                items,
                cluster=cluster,
                admin_prefix=self._admin_prefix,
            ):
                cluster_nav = build_secondary_nav(
                    items,
                    current_path,
                    cluster=cluster,
                    admin_prefix=self._admin_prefix,
                )
        for cluster, items in items_by_cluster.items():
            assembler_nav_items = collapse_cluster_in_primary(
                assembler_nav_items,
                current_path,
                items,
                cluster=cluster,
            )

        builder_items = self._nav_builder.build_nav_items(current_path=current_path)
        system_menu_items = self._nav_builder.build_system_menu_items()

        merged = list(builder_items)
        seen_hrefs: set[str] = set()
        group_labels: dict[str, set[str]] = {}
        current_group = ""

        for item in merged:
            if not isinstance(item, dict):
                continue
            if item.get("is_group"):
                current_group = item.get("label", "") or ""
                group_labels.setdefault(current_group, set())
            else:
                href = (item.get("href", "") or "").strip()
                if href:
                    seen_hrefs.add(href)
                label = (item.get("label", "") or "").strip()
                if label:
                    group_labels.setdefault(current_group, set()).add(label)

        top_items: list[dict] = []
        for item in assembler_nav_items:
            if not isinstance(item, dict):
                continue
            if item.get("is_group"):
                break
            href = (item.get("href", "") or "").strip()
            label = (item.get("label", "") or "").strip()
            if current_path is not None and href:
                item["active"] = current_path == href or current_path.startswith(
                    href + "/"
                )
            if href:
                seen_hrefs.add(href)
            if label:
                group_labels.setdefault("", set()).add(label)
            top_items.append(item)

        merged = top_items + merged

        current_group = ""
        for item in assembler_nav_items:
            if not isinstance(item, dict):
                merged.append(item)
                continue

            if item.get("is_group"):
                group_label = (item.get("label", "") or "").strip()
                current_group = group_label
                if group_label in group_labels:
                    continue
                group_labels.setdefault(current_group, set())
                merged.append(item)
                continue

            href = (item.get("href", "") or "").strip()
            label = (item.get("label", "") or "").strip()

            if href and href in seen_hrefs:
                continue
            if label and label in group_labels.get(current_group, set()):
                continue

            item["active"] = (
                current_path is not None
                and href
                and (current_path == href or current_path.startswith(href + "/"))
            )

            if href:
                seen_hrefs.add(href)
            if label:
                group_labels.setdefault(current_group, set()).add(label)
            merged.append(item)

        return merged, system_menu_items, cluster_nav

    # ------------------------------------------------------------------
    # User menu
    # ------------------------------------------------------------------

    def user_menu_items(
        self, include_plugins: bool = True
    ) -> list[dict[str, str | None]]:
        """Build the shell user-menu entries for this request.

        The Profile entry comes first, then cluster centers (one entry per
        registered cluster), then Plugins and Settings.

        Args:
            include_plugins: Include the Plugins landing entry (skipped by
                the placeholder/under-construction shell).

        Returns:
            Shell-compatible menu entry dicts (label, href, icon).
        """
        prefix = admin_prefix_from_request(self._request)
        entries: list[MenuItem] = [
            _menu_entry("Profile", prefix, "profile", "user-circle")
        ]
        entries.extend(
            _menu_entry(
                cluster.label,
                prefix,
                cluster.slug,
                cluster.icon or "box",
            )
            for cluster in self._cluster_registry.all()
        )
        if self._is_super_admin():
            entries.append(_menu_entry("Users", prefix, "users", "users"))
            entries.append(_menu_entry("Roles", prefix, "roles", "shield-check"))
            entries.append(_menu_entry("Security", prefix, "security", "shield"))
        if include_plugins:
            entries.append(_menu_entry("Plugins", prefix, "plugins", "plugins"))
        entries.append(_menu_entry("Settings", prefix, "settings", "settings"))
        return [entry.to_dict() for entry in entries]

    def _is_super_admin(self) -> bool:
        """True when the request user may see superadmin-only menu entries.

        Mirrors the authorization middleware's superadmin test: the literal
        ``is_superuser`` flag or the configured super-admin role (exposed on
        app state by the mount pipeline). Fail-closed: no user, no entry.
        """
        user = getattr(getattr(self._request, "state", None), "user", None)
        if user is None:
            return False
        if getattr(user, "is_superuser", False) is True:
            return True
        role = str(
            getattr(self._state, "super_admin_role", "") if self._state else ""
        )
        if not role:
            return False
        roles = getattr(user, "roles", None) or ()
        return role in roles
