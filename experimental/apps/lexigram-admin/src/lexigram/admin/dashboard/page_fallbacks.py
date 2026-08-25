"""Fallback rendering for admin pages without an implemented handler.

Contains the "Under Construction" placeholder page and the best-effort
branding color resolver shared by the page handler wrappers.
"""

from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.admin.state.context import wants_fragment
from lexigram.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_PRIMARY_COLOR = "#6b7280"


async def _resolve_primary_color(container: Any) -> str:
    """Resolve the saved branding primary color, best-effort.

    Falls back to the framework default when no registry/db store is
    available.
    """
    try:
        from lexigram.admin.settings.panel.registry import ConfigRegistry

        registry = await container.resolve(
            ConfigRegistry,
            bypass_visibility=True,
        )
        values = await registry.get_values("admin.branding", "db")
        color = values.get("primary_color")
        if color:
            return str(color)
    except Exception:  # noqa: BLE001 — non-fatal
        logger.exception("admin.theme_overrides_failed")
    return _DEFAULT_PRIMARY_COLOR


async def _placeholder_page(
    request: Any,
    container: Any | None = None,
) -> HTMLResponse:
    """Placeholder for admin pages without an implemented handler.

    For HTMX requests returns only the content fragment (no shell) so
    the sidebar/topbar from the existing page stays intact.  For direct
    navigation returns the full admin layout.

    Args:
        request: Starlette request.
        container: Optional resolver for theme settings.
    """
    content = (
        '<div class="flex items-center justify-center h-64">'
        '<div class="text-center">'
        '<h2 class="text-xl font-semibold text-muted-foreground">Under Construction</h2>'
        '<p class="text-muted-foreground mt-2">This page has not been implemented yet.</p>'
        "</div></div>"
    )

    try:
        from lexigram.admin.engine.renderer import resolve_admin_nav

        nav_items, system_menu_items, secondary_nav = resolve_admin_nav(request)
    except Exception:  # noqa: BLE001 — non-fatal
        nav_items, system_menu_items, secondary_nav = [], [], None

    if secondary_nav:
        from lexigram.admin.ui.organisms.secondary_nav import ClusterLayout
        from lexigram.ui import raw, render_to_string

        content = render_to_string(
            ClusterLayout(items=secondary_nav, content=raw(content))
        )

    is_htmx = wants_fragment(request)

    if is_htmx:
        return HTMLResponse(content)

    try:
        from pathlib import Path

        from starlette.templating import Jinja2Templates

        from lexigram.admin.ui.templates.shell import AdminShell
        from lexigram.ui import render_to_string

        user = (
            getattr(request.state, "user", None) if hasattr(request, "state") else None
        )

        from lexigram.admin.navigation.manager import NavigationManager

        user_menu_items = (
            NavigationManager(request).user_menu_items(include_plugins=False)
            if request is not None
            else []
        )

        theme_css = ""
        try:
            from lexigram.admin.theme.service import AdminThemeService

            service = AdminThemeService(
                primary_color=(
                    await _resolve_primary_color(container)
                    if container is not None
                    else _DEFAULT_PRIMARY_COLOR
                )
            )
            theme_css = service.generate_theme_css()
        except Exception:  # noqa: BLE001, S110 — non-fatal
            pass

        shell = AdminShell(
            content=content,
            title="Under Construction",
            user=user,
            nav_items=nav_items,
            system_menu_items=system_menu_items,
            user_menu_items=user_menu_items,
            theme_css=theme_css,
        )
        shell_html = render_to_string(shell)

        templates_dir = Path(__file__).resolve().parent.parent / "views" / "templates"
        templates = Jinja2Templates(directory=str(templates_dir))
        return templates.TemplateResponse(
            request,
            "admin_shell.html",
            context={
                "content": shell_html,
                "title": "Under Construction",
                "dark_mode": "",
            },
        )
    except Exception:  # noqa: BLE001 — rendering must never break the response
        return HTMLResponse(content)
