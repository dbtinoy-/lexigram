"""Admin page renderer for lexigram-admin.

Provides the AdminRenderer class that handles rendering admin pages
with proper layouts, navigation, and HTMX support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import HTMLResponse

if TYPE_CHECKING:
    from collections.abc import Callable

try:
    from markupsafe import Markup
except ImportError:
    Markup = str  # type: ignore[misc,assignment]


def resolve_admin_nav(request: Any) -> tuple[list, list, list | None]:
    """Resolve nav items, system menu items, and cluster secondary nav.

    Merges NavItemBuilder resource items with NavigationAssembler contributor
    navigation items. Active-state detection is computed per-request based on
    the current URL path.

    Cluster groups (e.g. infrastructure) are collapsed in the primary sidebar
    into single landing entries; when the current path belongs to a cluster
    center, the secondary nav for that center is returned as the third
    element.

    Duplicates are removed at three levels:
    1. Group header dedup — assembler group headers that match builder
       group headers are skipped.
    2. Label dedup — assembler items with the same label+group as a
       builder item are skipped (handles URL mismatches between
       namespaced resource URLs and hardcoded contributor URLs).
    3. URL dedup — any remaining item with the same href as an already-
       included item is skipped (catches all same-URL duplicates).

    Args:
        request: The current request (Starlette Request).

    Returns:
        A tuple of (nav_items, system_menu_items, secondary_nav).
    """
    from lexigram.admin.navigation.manager import NavigationManager

    return NavigationManager(request).resolve_nav()


@dataclass
class AdminRendererConfig:
    """Configuration for AdminRenderer."""

    # Site branding
    site_name: str = "Lexigram Admin"
    site_logo: str | None = None

    # Layout options
    show_sidebar: bool = True
    show_breadcrumbs: bool = True

    # Theme
    primary_color: str = "#6b7280"
    theme: str = "default"

    # Custom CSS/JS
    extra_css: list[str] = field(default_factory=list)
    extra_js: list[str] = field(default_factory=list)

    # Footer
    footer_text: str = ""


class AdminRenderer:
    """Renderer for admin pages.

    Handles:
    - Wrapping content in admin layout
    - Breadcrumb navigation
    - Background context (user info, navigation)
    - HTMX partial rendering support

    Usage:
        renderer = AdminRenderer(config)
        response = renderer.render_page(content, request, title="Dashboard")
    """

    def __init__(
        self,
        config: AdminRendererConfig | None = None,
        layout_builder: Callable[..., str | Markup] | None = None,
    ):
        """Initialize renderer.

        Args:
            config: Renderer configuration
            layout_builder: Custom layout builder function
        """
        self.config = config or AdminRendererConfig()
        self._layout_builder = layout_builder

    def render_page(
        self,
        content: str | Markup | Any,
        request: Request | None = None,
        title: str = "",
        breadcrumbs: list[dict[str, str]] | None = None,
        **extra_context: Any,
    ) -> HTMLResponse:
        """Render an admin page with layout.

        Args:
            content: Page content (HTML string or component)
            request: Current request (for user context)
            title: Page title
            breadcrumbs: Breadcrumb navigation items
            **extra_context: Additional context for layout

        Returns:
            HTMLResponse with rendered page
        """
        from lexigram.admin.navigation.manager import NavigationManager
        from lexigram.admin.state.context import AdminContextManager
        from lexigram.admin.ui.templates.shell import AdminShell
        from lexigram.ui.core.base import render_to_string

        user = getattr(request.state, "user", None) if request else None

        nav_items, system_menu_items, _ = resolve_admin_nav(request)

        # Read flash messages from request context and consume them
        ctx = AdminContextManager.get_context()
        flash_messages: list[dict[str, str]] = []
        if ctx:
            flash_messages = list(ctx.flash_messages)
            ctx.flash_messages.clear()

        # Generate theme CSS from config primary_color (overridable per request)
        theme_css = ""
        try:
            from lexigram.admin.theme.service import AdminThemeService

            primary_color = (
                extra_context.get("primary_color")
                or self.config.primary_color
                or "#6b7280"
            )
            service = AdminThemeService(primary_color=primary_color)
            theme_css = service.generate_theme_css()
        except Exception:  # noqa: BLE001, S110 — non-fatal
            pass

        user_menu_items: list[dict[str, str | None]] = (
            NavigationManager(request).user_menu_items() if request is not None else []
        )

        site_name = extra_context.get("site_name") or self.config.site_name
        logo_url = extra_context.get("logo_url") or ""
        favicon_url = extra_context.get("favicon_url") or ""
        dark_mode = extra_context.get("dark_mode") or ""
        impersonation_active = bool(extra_context.get("impersonation_active"))
        impersonation_target_id = str(
            extra_context.get("impersonation_target_id") or ""
        )
        csrf_token = getattr(request.state, "csrf_token", None) if request else None

        shell = AdminShell(
            content=content,
            title=title,
            user=user,
            nav_items=nav_items,
            user_menu_items=user_menu_items,
            system_menu_items=system_menu_items,
            breadcrumbs=breadcrumbs,
            flash_messages=flash_messages,
            theme_css=theme_css,
            site_name=site_name,
            logo_url=logo_url,
            dark_mode=dark_mode,
            impersonation_active=impersonation_active,
            impersonation_target_id=impersonation_target_id,
            csrf_token=csrf_token or "",
        )

        # Prepare templates
        from pathlib import Path

        from starlette.templating import Jinja2Templates

        # Resolve templates directory relative to this file
        # lexigram/admin/engine/renderer.py -> lexigram/admin/views/templates
        templates_dir = Path(__file__).parent.parent / "views" / "templates"
        templates = Jinja2Templates(directory=str(templates_dir))

        shell_html = Markup(render_to_string(shell))

        # Render using template
        return templates.TemplateResponse(
            request,  # type: ignore[arg-type]
            "admin_shell.html",
            context={
                "content": shell_html,
                "title": title,
                "site_name": site_name,
                "favicon_url": favicon_url,
                "dark_mode": dark_mode,
                "csrf_token": csrf_token,
            },
        )

    def render_partial(
        self,
        content: str | Markup | Any,
        headers: dict[str, str] | None = None,
    ) -> HTMLResponse:
        """Render a partial for HTMX requests.

        Args:
            content: Partial content
            headers: Optional HTMX response headers

        Returns:
            HTMLResponse with partial content
        """
        if hasattr(content, "__html__"):
            content_str = str(content.__html__())
        else:
            content_str = str(content)

        return HTMLResponse(content_str, headers=headers or {})
