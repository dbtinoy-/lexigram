"""Structural section builders for AdminShell (nav, layout chrome)."""

from __future__ import annotations

from typing import Any

from lexigram.admin.ui.organisms.sidebar import SidebarItem
from lexigram.ui import el


def prepare_navigation(
    nav_items: list[Any],
    features: dict[str, bool],
    user: Any,
) -> list[Any]:
    """Transform raw nav_items into SidebarItem and SidebarSection instances.

    Args:
        nav_items: Raw navigation entries (dicts, tuples or SidebarNavItem).
        features: Feature-flag map used to hide gated entries.
        user: Authenticated user used for permission filtering.

    Returns:
        Flat list of SidebarItem/SidebarSection ready for the Sidebar.
    """
    from lexigram.admin.navigation.types import SidebarNavItem
    from lexigram.admin.ui.organisms.sidebar import SidebarSection

    items = []
    current_section = None

    for item in nav_items:
        if isinstance(item, SidebarNavItem):
            item = item.to_dict()

        if not isinstance(item, dict):
            if isinstance(item, tuple):
                items.append(SidebarItem(label=item[0], href=item[1]))
            continue

        # Handle Group Header
        if item.get("is_group"):
            current_section = SidebarSection(title=item.get("label", ""), items=[])
            items.append(current_section)  # type: ignore[arg-type]
            continue

        # Determine permission requirement
        href = item.get("href", "")
        required_permission = item.get("permission")
        required_feature = item.get("feature")

        # Check if required feature is enabled
        if required_feature:
            feature_key = f"{required_feature}_enabled"
            if not features.get(feature_key, True):
                continue

        # If no explicit permission, try to infer from resource URL
        if not required_permission and href and "/admin//" in href:
            parts = href.split("/")
            try:
                idx = parts.index("api")
                if len(parts) > idx + 1:
                    resource = parts[idx + 1]
                    required_permission = f"{resource}.read"
            except (ValueError, IndexError):
                pass

        # Check permission if required
        if required_permission and user:
            try:
                from lexigram.admin.auth.rbac import (  # type: ignore[import-untyped]
                    RBACChecker,  # noqa: F401  # imported for optional runtime check only
                )
            except ImportError:
                rbac_checker = None

            if rbac_checker and not rbac_checker.has_permission(
                user,
                required_permission,
            ):
                continue

        # Build SidebarItem
        sidebar_item = SidebarItem(
            label=item.get("label", ""),
            href=href,
            icon=item.get("icon"),
            badge=item.get("badge"),
            active=item.get("active", False),
        )

        if current_section:
            current_section.items.append(sidebar_item)
        else:
            items.append(sidebar_item)

    # Filter out empty sections
    final_items = []
    for item in items:
        if isinstance(item, SidebarSection) and not item.items:
            continue
        final_items.append(item)
    return final_items


def build_sidebar_container(sidebar_html: Any) -> Any:
    """Wrap the rendered sidebar in the responsive drawer container."""
    return el(
        "div",
        # Overlay for mobile
        el(
            "div",
            class_="fixed inset-0 z-30 bg-muted/50 backdrop-blur-sm lg:hidden",
            x_show="sidebarOpen",
            x_transition_enter="transition-opacity ease-linear duration-300",
            x_transition_enter_start="opacity-0",
            x_transition_enter_end="opacity-100",
            x_transition_leave="transition-opacity ease-linear duration-300",
            x_transition_leave_start="opacity-100",
            x_transition_leave_end="opacity-0",
            **{"x-on:click": "sidebarOpen = false"},
            aria_hidden="true",
        ),
        # Sidebar drawer
        el(
            "div",
            sidebar_html,
            class_="fixed inset-y-0 left-0 z-40 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0 bg-transparent lg:pointer-events-auto",
            **{
                # Enable pointer events when the sidebar is open on small screens; keep auto on lg
                "x-bind:class": "sidebarOpen ? 'translate-x-0 pointer-events-auto' : '-translate-x-full pointer-events-none'",
            },
        ),
        class_="lg:flex lg:flex-shrink-0",
    )


def build_impersonation_banner(active: bool, target_id: str, csrf_token: str) -> Any:
    """Build the impersonation notice banner, or an empty string when inactive."""
    return (
        el(
            "div",
            el(
                "span",
                f"Impersonating {target_id}",
                class_="font-medium",
            ),
            el(
                "form",
                el(
                    "input",
                    type_="hidden",
                    name="csrf_token",
                    value=csrf_token or "",
                ),
                el(
                    "button",
                    "Stop impersonating",
                    type="submit",
                    class_=(
                        "ml-4 px-3 py-1 text-xs font-medium rounded-md "
                        "bg-white/20 hover:bg-white/30 transition-colors"
                    ),
                ),
                method="post",
                action="/admin/impersonate/stop",
                class_="inline-flex items-center",
            ),
            class_=(
                "flex items-center justify-between px-4 py-2 text-sm text-white "
                "bg-amber-600 dark:bg-amber-700"
            ),
        )
        if active
        else ""
    )


def build_main_area(
    topbar_html: Any,
    impersonation_banner: Any,
    breadcrumbs: list[dict[str, Any]],
    content_inner: Any,
) -> Any:
    """Build the main content column: topbar, banner, breadcrumbs and body."""
    return el(
        "div",
        topbar_html,
        impersonation_banner,
        # Breadcrumbs
        *build_breadcrumbs_nav(breadcrumbs),
        el(
            "main",
            el("div", content_inner, id="main-content", class_="px-4 py-4"),
            class_="flex-1 overflow-y-auto bg-muted dark:bg-muted focus:outline-none transition-colors duration-300",
        ),
        class_="flex flex-col flex-1 min-w-0 overflow-hidden",
    )


def build_breadcrumbs_nav(breadcrumbs: list[dict[str, Any]]) -> list[Any]:
    """Build the breadcrumb trail nodes for the main area."""
    return (
        [
            el(
                "div",
                el(
                    "nav",
                    {"class": "flex text-muted-foreground text-xs mb-4"},
                    [
                        el(
                            "div",
                            {"class": "flex items-center"},
                            el(
                                "a",
                                {
                                    "href": b["url"],
                                    "class": "hover:text-primary",
                                }
                                if b["url"]
                                else {},
                                b["label"],
                            ),
                            el("span", {"class": "mx-2"}, "/")
                            if i < len(breadcrumbs) - 1
                            else "",
                        )
                        for i, b in enumerate(breadcrumbs)
                    ],
                ),
                class_="px-4 mt-2",
            )
        ]
        if breadcrumbs
        else []
    )


def build_root_data_attrs(dm_expr: str) -> dict[str, str]:
    """Build the Alpine root attributes for the shell wrapper div."""
    return {
        "x-data": "{ sidebarOpen: false, sidebarMini: localStorage.getItem('sidebarMini') === 'true', darkMode: "
        + dm_expr
        + " }",
        "x-init": "$watch('darkMode', val => { localStorage.setItem('darkMode', val); document.documentElement.classList.toggle('dark', val) }); $watch('sidebarMini', val => localStorage.setItem('sidebarMini', val)); document.documentElement.classList.toggle('dark', darkMode)",
        "x-on:darkmode-change.window": "darkMode = $event.detail.dark",
        "class": "flex h-screen overflow-hidden bg-background transition-colors duration-300 font-sans text-foreground",
        "x-on:beforeunload.window": "window.notificationEventSource?.close()",
    }
