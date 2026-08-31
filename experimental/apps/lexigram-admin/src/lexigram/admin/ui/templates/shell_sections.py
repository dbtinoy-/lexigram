"""Structural section builders for AdminShell (nav, layout chrome)."""

from __future__ import annotations

from typing import Any

from lexigram.admin.ui.organisms.sidebar import SidebarItem
from lexigram.ui import el


def _user_has_permission(user: Any, permission: str) -> bool:
    """Check a permission against the shell ``user`` (dict or record).

    Supports the ``has_permission`` protocol (e.g.
    :class:`~lexigram.admin.auth.user.AdminUserRecord`) and plain
    dicts with a ``permissions`` list (or a list passed as ``user``).
    """
    if not user:
        return False

    if isinstance(user, dict):
        perms = user.get("permissions") or []
        return permission in perms or (
            "*" in perms if isinstance(perms, list) else False
        )

    has_perm = getattr(user, "has_permission", None)
    if callable(has_perm):
        try:
            return bool(has_perm(permission))
        except TypeError:
            return False

    if isinstance(user, (list, tuple, set, frozenset)):
        return permission in user or "*" in user

    perms = getattr(user, "permissions", None)
    if isinstance(perms, (list, tuple, set, frozenset)):
        return permission in perms or "*" in perms
    return False


def prepare_navigation(
    nav_items: list[Any],
    features: dict[str, bool],
    user: Any,
    admin_prefix: str = "/admin",
) -> list[Any]:
    """Transform raw nav_items into SidebarItem and SidebarSection instances.

    Args:
        nav_items: Raw navigation entries (dicts, tuples or SidebarNavItem).
        features: Feature-flag map used to hide gated entries.
        user: Authenticated user used for permission filtering.
        admin_prefix: Configured admin mount prefix used to infer resource
            permissions from item hrefs.

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

        # If no explicit permission, try to infer from resource URL.
        # Resource nav links are ``{admin_prefix}/{resource}`` — derive the
        # ``{resource}.read`` permission from the first path segment after
        # the configured admin prefix (works for any mount prefix).
        if (
            not required_permission
            and href
            and href.startswith(admin_prefix.rstrip("/") + "/")
        ):
            remainder = href[len(admin_prefix.rstrip("/")) + 1 :]
            resource = remainder.split("/", 1)[0].split("?")[0]
            if resource:
                required_permission = f"{resource}.read"

        # Check permission if required. The user record (or dict) carries its
        # own permission list; legacy RBACChecker was removed — authorization
        # is provided by the request/session user object.
        if (
            required_permission
            and user
            and not _user_has_permission(user, required_permission)
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


def build_impersonation_banner(
    active: bool,
    target_id: str,
    csrf_token: str,
    admin_prefix: str = "/admin",
) -> Any:
    """Build the impersonation notice banner, or an empty string when inactive.

    Acting as another user is the highest-consequence state in the admin:
    every action taken is attributed to the impersonated account. The banner
    is therefore a live region so the state is announced when it appears,
    and it names the mechanism explicitly rather than relying on colour
    alone to signal that this session is not the operator's own.
    """
    if not active:
        return ""

    return el(
        "div",
        el(
            "div",
            el(
                "svg",
                el(
                    "path",
                    **{
                        "fill-rule": "evenodd",
                        "clip-rule": "evenodd",
                        "d": (
                            "M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c."
                            "75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646"
                            "-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0z"
                            "m-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                        ),
                    },
                ),
                viewBox="0 0 20 20",
                fill="currentColor",
                class_="w-4 h-4 flex-shrink-0",
                **{"aria-hidden": "true", "focusable": "false"},
            ),
            el(
                "span",
                el("span", "Impersonating", class_="font-semibold"),
                " ",
                # The identifier is the one piece of data that tells the
                # operator whose account they are acting as, so it is set
                # apart from the surrounding sentence rather than run
                # together with it.
                el("span", target_id, class_="font-mono"),
                el(
                    "span",
                    ". Actions you take are recorded against this account.",
                    class_="sr-only",
                ),
            ),
            class_="flex items-center gap-2 min-w-0",
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
                    "bg-white/20 hover:bg-white/30 transition-colors "
                    "focus-visible:outline-none focus-visible:ring-2 "
                    "focus-visible:ring-white focus-visible:ring-offset-2 "
                    "focus-visible:ring-offset-amber-700"
                ),
                **{"aria-label": f"Stop impersonating {target_id}"},
            ),
            method="post",
            action=f"{admin_prefix.rstrip('/') or '/admin'}/impersonate/stop",
            class_="inline-flex items-center flex-shrink-0",
        ),
        # amber-700 rather than amber-600: white on amber-600 measures
        # 3.19:1, below the 4.5:1 WCAG AA minimum for body text. amber-700
        # is 5.02:1 and amber-800 is 7.09:1.
        class_=(
            "flex items-center justify-between gap-3 px-4 py-2 text-sm "
            "text-white bg-amber-700 dark:bg-amber-800"
        ),
        role="status",
        **{"aria-live": "polite", "data-impersonation-banner": "true"},
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
            el(
                "div",
                content_inner,
                id="main-content",
                class_="admin-shell-content px-4 py-4",
            ),
            class_="admin-shell-scroll flex-1 overflow-y-auto bg-muted dark:bg-muted focus:outline-none transition-colors duration-300",
        ),
        class_="admin-shell-main flex flex-col flex-1 min-w-0 overflow-hidden",
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
                class_="admin-breadcrumbs px-4 mt-2",
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
        "class": "admin-shell-root flex h-screen overflow-hidden bg-background transition-colors duration-300 font-sans text-foreground",
        "x-on:beforeunload.window": "window.notificationEventSource?.close()",
    }
