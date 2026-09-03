"""Per-request navigation mount for the admin shell.

:class:`NavigationManager` is the single per-request entry point for
navigation state: it resolves the primary nav (resource items + assembler
contributions with dedup, placement, and per-request active state), the cluster
secondary sidebar for the active cluster center, the sidebar utility links, and
the personal user-menu entries as :class:`MenuItem` values.

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
    """Build a shell navigation entry under the configured admin prefix."""
    base = (prefix or DEFAULT_ADMIN_PREFIX).rstrip("/")
    href = f"{base}/{suffix.lstrip('/')}"
    return MenuItem(label=label, href=href, icon=icon)


def _primary_menu_entry(
    label: str,
    prefix: str,
    suffix: str,
    icon: str,
) -> dict[str, Any]:
    """Build a generated primary entry with explicit auth semantics."""
    entry: dict[str, Any] = _menu_entry(label, prefix, suffix, icon).to_dict()
    entry["skip_permission_inference"] = True
    return entry


# Known shell groups get a stable visual order. Unknown consumer groups retain
# their relative order after these sections, so contributors can extend the
# sidebar without being silently reordered alphabetically.
_PRIMARY_GROUP_ORDER: dict[str, int] = {
    "workspace": 10,
    "operations": 20,
    "security": 30,
    "integrations": 40,
    "search": 50,
    "tools": 50,
    "administration": 90,
}


def _group_order(label: object) -> int:
    """Return the presentation rank for a primary sidebar group."""
    return _PRIMARY_GROUP_ORDER.get(str(label or "").strip().casefold(), 60)


def _order_primary_nav(items: list[Any]) -> list[Any]:
    """Order complete sidebar sections without disturbing item order.

    Top-level links remain at the top. Grouped sections are treated as
    indivisible blocks, then ranked by the shell's information architecture;
    unrecognized groups retain their original relative ordering.
    """
    leading: list[Any] = []
    blocks: list[tuple[int, int, list[Any]]] = []
    current: list[Any] | None = None
    current_rank = 60
    section_index = 0

    for item in items:
        if isinstance(item, dict) and item.get("is_group"):
            if current is not None:
                blocks.append((current_rank, section_index, current))
                section_index += 1
            current = [item]
            current_rank = _group_order(item.get("label"))
        elif current is None:
            leading.append(item)
        else:
            current.append(item)

    if current is not None:
        blocks.append((current_rank, section_index, current))

    blocks.sort(key=lambda block: (block[0], block[1]))
    return leading + [item for _rank, _index, block in blocks for item in block]


def _append_unique_group(
    items: list[Any],
    label: str,
    entries: list[dict[str, Any]],
) -> None:
    """Append a labeled group while avoiding duplicate destinations."""
    existing_hrefs = {
        str(item.get("href", "")).strip()
        for item in items
        if isinstance(item, dict) and item.get("href")
    }
    unique_entries: list[dict[str, Any]] = []
    for entry in entries:
        href = str(entry.get("href", "")).strip()
        if href and href in existing_hrefs:
            continue
        unique_entries.append(entry)
        if href:
            existing_hrefs.add(href)

    if unique_entries:
        items.append({"is_group": True, "label": label})
        items.extend(unique_entries)


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
        # An explicitly supplied empty registry is meaningful (for example,
        # an installation that disables optional centers); only fall back to
        # built-ins when app state has not provided a real registry.
        self._cluster_registry = (
            registry
            if isinstance(registry, ClusterRegistry)
            else ClusterRegistry.with_defaults()
        )

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
        contributor items, computes per-request active states, promotes
        registered cluster centers into the primary sidebar, and — when the
        path belongs to a cluster center — returns its secondary nav.

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
        cluster_landing_items: list[tuple[int, int, dict[str, Any]]] = []
        items_by_cluster: dict[Any, list] = {}
        for cluster_index, cluster in enumerate(self._cluster_registry.all()):
            items = cluster_items(self._assembler_groups, cluster=cluster)
            # A registered center is a destination even when no contributor
            # has populated it yet; its controller can render an empty state.
            items_by_cluster[cluster] = items
            cluster_slug = str(
                getattr(cluster, "slug", None)
                or getattr(cluster, "name", "cluster")
            ).strip("/") or "cluster"
            cluster_label = (
                getattr(cluster, "label", None)
                or getattr(cluster, "name", None)
                or "Operations"
            )
            cluster_landing_items.append(
                (
                    int(getattr(cluster, "order", 0) or 0),
                    cluster_index,
                    {
                        "label": cluster_label,
                        "href": f"{self._admin_prefix}/{cluster_slug}",
                        "icon": getattr(cluster, "icon", None) or "server",
                        # Cluster centers and their global auth boundary are
                        # managed by the registry/middleware, not inferred as
                        # resource permissions from their landing URL.
                        "skip_permission_inference": True,
                        "active": is_cluster_path(
                            current_path,
                            items,
                            cluster=cluster,
                            admin_prefix=self._admin_prefix,
                        ),
                    },
                )
            )
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
        cluster_landing_items.sort(key=lambda item: (item[0], item[1]))
        for cluster, items in items_by_cluster.items():
            assembler_nav_items = collapse_cluster_in_primary(
                assembler_nav_items,
                current_path,
                items,
                cluster=cluster,
            )

        builder_items = self._nav_builder.build_nav_items(current_path=current_path)
        system_menu_items = self._build_system_menu_items(
            self._nav_builder.build_system_menu_items(),
            current_path,
        )

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

        visible_cluster_items = [
            item
            for _order, _index, item in cluster_landing_items
            if not item["href"] or item["href"] not in seen_hrefs
        ]
        for item in visible_cluster_items:
            if item.get("href"):
                seen_hrefs.add(str(item["href"]))
        if visible_cluster_items:
            top_items.append({"is_group": True, "label": "Operations"})
            top_items.extend(visible_cluster_items)

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

        # Plugins is a destination, not an account action. Keep it visible in
        # the sidebar while preserving the existing user-menu API for direct
        # integrations that still request the full navigation set.
        _append_unique_group(
            merged,
            "Tools",
            [
                _primary_menu_entry(
                    "Plugins",
                    self._admin_prefix,
                    "plugins",
                    "plugins",
                ),
            ],
        )

        # Administrative destinations are deliberately request-gated here so
        # the shell never renders a privileged link to a regular operator.
        if self._is_super_admin():
            _append_unique_group(
                merged,
                "Administration",
                [
                    _primary_menu_entry(
                        "Users", self._admin_prefix, "users", "users"
                    ),
                    _primary_menu_entry(
                        "Roles", self._admin_prefix, "roles", "shield-check"
                    ),
                    _primary_menu_entry(
                        "Security", self._admin_prefix, "security", "shield"
                    ),
                    _primary_menu_entry(
                        "Email", self._admin_prefix, "email", "mail"
                    ),
                ],
            )

        return _order_primary_nav(merged), system_menu_items, cluster_nav

    def _build_system_menu_items(
        self,
        supplied_items: list[Any],
        current_path: str | None,
    ) -> list[dict[str, Any]]:
        """Build the persistent sidebar utility area.

        Settings is a global application destination rather than a personal
        account action, so it belongs in the sidebar footer. Consumer-supplied
        system links remain supported and win when they already provide a
        Settings entry.
        """
        settings: dict[str, Any] = _menu_entry(
            "Settings",
            self._admin_prefix,
            "settings",
            "settings",
        ).to_dict()
        settings["render"] = "block"
        settings["active"] = bool(
            current_path
            and (
                current_path == settings["href"]
                or current_path.startswith(str(settings["href"]) + "/")
            )
        )

        normalized: list[dict[str, Any]] = []
        existing_hrefs: set[str] = set()
        existing_labels: set[str] = set()
        for item in supplied_items:
            if not isinstance(item, dict):
                continue
            normalized_item = dict(item)
            if normalized_item.get("href"):
                normalized_item["href"] = mount_admin_url(
                    str(normalized_item["href"]), self._admin_prefix
                )
            if normalized_item.get("badge"):
                normalized_item["badge"] = mount_admin_url(
                    str(normalized_item["badge"]), self._admin_prefix
                )
            href = str(normalized_item.get("href", "")).strip()
            label = str(normalized_item.get("label", "")).strip().casefold()
            if href and href in existing_hrefs:
                continue
            if label and label in existing_labels:
                continue
            if (
                current_path
                and href
                and (current_path == href or current_path.startswith(href + "/"))
            ):
                normalized_item["active"] = True
            normalized.append(normalized_item)
            if href:
                existing_hrefs.add(href)
            if label:
                existing_labels.add(label)

        if (
            str(settings["href"]) not in existing_hrefs
            and "settings" not in existing_labels
        ):
            normalized.insert(0, settings)
        return normalized

    # ------------------------------------------------------------------
    # User menu
    # ------------------------------------------------------------------

    def user_menu_items(
        self,
        include_plugins: bool = True,
        *,
        include_navigation: bool = True,
    ) -> list[dict[str, str | None]]:
        """Build the shell user-menu entries for this request.

        The Profile entry is always first. When ``include_navigation`` is
        true, the legacy full set (cluster centers, superadmin destinations,
        Plugins, and Settings) is also returned for direct API callers. The
        rendered shell passes ``include_navigation=False`` because those
        application destinations now live in the sidebar.

        Args:
            include_plugins: Include the Plugins landing entry in the legacy
                full set (skipped by the placeholder shell).
            include_navigation: Keep application navigation entries in this
                menu. Set false for the shell's personal account menu.

        Returns:
            Shell-compatible menu entry dicts (label, href, icon).
        """
        prefix = admin_prefix_from_request(self._request)
        entries: list[MenuItem] = [
            _menu_entry("Profile", prefix, "profile", "user-circle")
        ]
        if not include_navigation:
            return [entry.to_dict() for entry in entries]

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
            entries.append(_menu_entry("Email", prefix, "email", "mail"))
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
        role = str(getattr(self._state, "super_admin_role", "") if self._state else "")
        if not role:
            return False
        roles = getattr(user, "roles", None) or ()
        return role in roles
