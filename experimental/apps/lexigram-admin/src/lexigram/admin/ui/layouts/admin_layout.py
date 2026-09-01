"""AdminLayout - Main layout wrapper for admin pages.

This module provides the AdminLayout class that renders admin pages with:
- HTML head with meta, CSS, JS
- Navigation header
- Sidebar navigation
- Main content area
- Footer
- Toast notifications area

Uses inheritance from BaseLayout for code reuse.

UI-08: AdminLayout implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from markupsafe import Markup, escape

from lexigram.admin.theme.tailwind import (
    DARK_BOOTSTRAP_SCRIPT,
    THEME_BRIDGE_SCRIPT,
)
from lexigram.admin.ui.layouts.components import (
    FooterConfig,
    FooterRenderer,
    HeaderConfig,
    HeaderRenderer,
    NavGroup,
    NavItem,
    ServerToastChannel,
    SidebarConfig,
    SidebarRenderer,
    ToastConfig,
    UserInfo,
    flash_to_toast,
)
from lexigram.ui import BaseLayoutConfig, BaseLayoutContext, LayoutBase, js_string


@dataclass
class AdminLayoutConfig(BaseLayoutConfig):
    """Configuration for admin layout.

    Extends BaseLayoutConfig with admin-specific options.
    """

    # Branding
    app_name: str = "Admin"
    app_logo: str | None = None
    app_logo_alt: str = "Logo"

    # Layout options
    sidebar_collapsed: bool = False
    sidebar_width: str = "256px"
    sidebar_collapsed_width: str = "64px"
    fixed_header: bool = True
    fixed_sidebar: bool = True

    # Features
    show_search: bool = True
    show_notifications: bool = True
    show_user_menu: bool = True
    show_footer: bool = True
    show_breadcrumbs: bool = True


@dataclass
class NavItemConfig:
    """Navigation item configuration."""

    label: str
    url: str
    icon: str | None = None
    badge: str | None = None
    badge_variant: str = "primary"
    active: bool = False
    children: list[NavItemConfig] = field(default_factory=list)
    permission: str | None = None


@dataclass
class AdminLayoutContext(BaseLayoutContext):
    """Context for admin layout rendering.

    Extends BaseLayoutContext with admin-specific data.
    """

    # Current page
    page_title: str = "Dashboard"
    page_description: str | None = None

    # Current user
    user_name: str | None = None
    user_email: str | None = None
    user_avatar: str | None = None
    user_role: str | None = None

    # Navigation
    nav_items: list[NavItemConfig] = field(default_factory=list)
    current_path: str = "/"

    # URLs
    base_url: str = "/admin"
    logout_url: str = "/admin/logout"
    profile_url: str = "/admin/profile"
    settings_url: str = "/admin/settings"
    notifications_url: str = "/admin/notifications"

    # Notifications
    notifications: list[dict[str, Any]] = field(default_factory=list)
    unread_count: int = 0

    # Messages/Toasts
    flash_messages: list[tuple[str, str]] = field(default_factory=list)

    # CSRF
    csrf_token: str | None = None

    # State
    sidebar_collapsed: bool = False


class AdminLayout(LayoutBase):
    """Admin layout with sidebar, header, and footer.

    Extends BaseLayout with admin-specific components and rendering.
    """

    def __init__(
        self,
        config: AdminLayoutConfig | None = None,
        context: AdminLayoutContext | None = None,
    ):
        """Initialize admin layout.

        Args:
            config: Layout configuration
            context: Layout context with user, nav, etc.
        """
        self.admin_config = config or AdminLayoutConfig()
        self.admin_context = context or AdminLayoutContext()

        # Initialize base layout
        super().__init__(self.admin_config)

        # Set up component renderers
        self._setup_components()

    def _setup_components(self) -> None:
        """Set up layout component renderers."""
        ctx = self.admin_context
        cfg = self.admin_config

        # Header. Context URL fields retain precedence when callers provide
        # custom destinations; default values follow a custom base mount.
        base_url = ctx.base_url.rstrip("/") or "/admin"

        def _context_url(value: str, default_suffix: str) -> str:
            default = f"/admin/{default_suffix}"
            return f"{base_url}/{default_suffix}" if value == default else value

        self.header_renderer = HeaderRenderer(
            config=HeaderConfig(
                site_name=cfg.app_name,
                logo_url=cfg.app_logo,
                logo_alt=cfg.app_logo_alt,
                show_search=cfg.show_search,
                show_notifications=cfg.show_notifications,
                show_user_menu=cfg.show_user_menu,
                home_url=base_url,
                search_url=f"{base_url}/search",
                profile_url=_context_url(ctx.profile_url, "profile"),
                settings_url=_context_url(ctx.settings_url, "settings"),
                logout_url=_context_url(ctx.logout_url, "logout"),
                notifications_url=_context_url(ctx.notifications_url, "notifications"),
            ),
            user=UserInfo(
                name=ctx.user_name or "User",
                email=ctx.user_email or "",
                avatar_url=ctx.user_avatar,
                role=ctx.user_role,
            )
            if ctx.user_name
            else None,
        )

        # Sidebar
        nav_groups = self._build_nav_groups()
        self.sidebar_renderer = SidebarRenderer(
            config=SidebarConfig(
                width=cfg.sidebar_width,
                collapsed_width=cfg.sidebar_collapsed_width,
                default_collapsed=cfg.sidebar_collapsed,
                show_logo=False,  # Logo in header
                site_name=cfg.app_name,
            ),
            groups=nav_groups,
        )

        # Footer
        self.footer_renderer = FooterRenderer(
            config=FooterConfig(
                copyright_holder=cfg.app_name,
                show_version=False,
            ),
        )

        # Toast
        self.toast_renderer = ServerToastChannel(
            config=ToastConfig(
                position="top-right",
                default_duration_ms=5000,
            ),
        )

    def _build_nav_groups(self) -> list[NavGroup]:
        """Build navigation groups from NavItemConfig list."""
        items = [self._convert_nav_item(item) for item in self.admin_context.nav_items]

        if items:
            return [NavGroup(label=None, items=items)]
        return []

    def _convert_nav_item(self, item: NavItemConfig) -> NavItem:
        """Convert NavItemConfig to NavItem."""
        children = [self._convert_nav_item(child) for child in item.children]

        is_active = (
            item.active
            or self.admin_context.current_path == item.url
            or self.admin_context.current_path.startswith(item.url + "/")
        )

        return NavItem(
            label=item.label,
            url=item.url,
            icon=item.icon or "circle",
            badge=item.badge,
            badge_color="blue"
            if item.badge_variant == "primary"
            else item.badge_variant,
            is_active=is_active,
            children=children,
        )

    def render_head_content(self, **kwargs: Any) -> str:
        """Render additional head content.

        Returns admin-specific CSS and theme variables.
        """
        cfg = self.admin_config
        ctx = self.admin_context

        parts: list[str] = []

        # Page title
        parts.append(
            f"<title>{escape(ctx.page_title)} | {escape(cfg.app_name)}</title>",
        )

        if ctx.page_description:
            parts.append(
                f'<meta name="description" content="{escape(ctx.page_description)}">',
            )

        # Theme CSS variables
        parts.append(f"""
        <style>
            :root {{
                --admin-sidebar-width: {escape(cfg.sidebar_width)};
                --admin-sidebar-collapsed-width: {escape(cfg.sidebar_collapsed_width)};
            }}
        </style>
        """)

        # Tailwind CSS (static build). Derive asset URLs from the configured
        # mount so a deployment using /backoffice does not load /admin assets.
        asset_prefix = ctx.base_url.rstrip("/") or "/admin"
        parts.append(
            f'<link rel="stylesheet" href="{escape(asset_prefix)}/static/css/tailwind.css">'
        )
        parts.append(
            f'<link rel="stylesheet" href="{escape(asset_prefix)}/static/css/admin.css">'
        )
        parts.append(DARK_BOOTSTRAP_SCRIPT)
        parts.append(THEME_BRIDGE_SCRIPT)

        # Lucide icons — vendored locally (no third-party CDN, pinned version)
        parts.append(
            f'<script src="{escape(asset_prefix)}/static/js/lucide.min.js"></script>'
        )

        # SortableJS for dashboard widget drag-and-drop (vendored locally)
        parts.append(
            f'<script src="{escape(asset_prefix)}/static/js/sortable.min.js"></script>'
        )

        # Alpine.js plugins (loaded before Alpine core)
        parts.append(
            f'<script defer src="{escape(asset_prefix)}/static/js/alpine-focus.min.js"></script>',
        )
        # Alpine.js for dropdowns, modals, slide-overs
        parts.append(
            f'<script defer src="{escape(asset_prefix)}/static/js/alpine.min.js"></script>',
        )
        # Patch Alpine's transition handler to catch isFromCancelledTransition
        parts.append(
            "<script defer>var origToggle=Element.prototype._x_toggleAndCascadeWithTransitions;origToggle&&(Element.prototype._x_toggleAndCascadeWithTransitions=function(e,t,r,n){var o=origToggle.call(this,e,t,r,n);if(!t&&this._x_hidePromise)this._x_hidePromise.catch(function(a){});return o})</script>",
        )
        # Suppress Alpine's harmless transition-cancelled promise rejections
        parts.append(
            '<script>window.addEventListener("unhandledrejection",function(e){e.promise&&e.promise.catch(function(){});if(!e.reason)return;var r=e.reason;if(r.isFromCancelledTransition||r instanceof TypeError){e.preventDefault();e.stopImmediatePropagation()}})</script>',
        )

        return "\n".join(parts)

    def render_body_content(self, content: str = "", **kwargs: Any) -> str:
        """Render the body content.

        Args:
            content: Main page content

        Returns:
            Complete body inner HTML
        """
        cfg = self.admin_config
        ctx = self.admin_context

        parts: list[str] = []

        # Skip link for accessibility
        parts.append(
            '<a href="#main-content" class="skip-link sr-only focus:not-sr-only">Skip to content</a>',
        )

        # Layout wrapper
        collapsed_class = "sidebar-collapsed" if ctx.sidebar_collapsed else ""
        parts.append(f'<div class="admin-wrapper {collapsed_class}">')

        # Sidebar
        parts.append(self.sidebar_renderer.render(ctx.current_path))

        # Main area
        parts.append('<div class="admin-main">')

        # Header
        parts.append(
            self.header_renderer.render(
                notifications=ctx.notifications,
                unread_count=ctx.unread_count,
            ),
        )

        # Main content
        parts.append('<main id="main-content" class="admin-content">')
        parts.append(content)
        parts.append("</main>")

        # Footer
        if cfg.show_footer:
            parts.append(self.footer_renderer.render())

        parts.append("</div>")  # admin-main
        parts.append("</div>")  # admin-wrapper

        # Toast container with flash messages
        toasts = flash_to_toast(ctx.flash_messages)
        parts.append(self.toast_renderer.render_container(toasts))

        # Initialize Lucide icons
        parts.append("""
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                if (window.lucide) lucide.createIcons();
            });
        </script>
        """)

        # HTMX re-init icons after swap
        if cfg.htmx_enabled:
            csrf_header = ""
            if ctx.csrf_token:
                # js_string, not escape: this is script content, where the
                # HTML parser does not decode entities. An escaped quote
                # would reach JavaScript as the literal text "&#39;" and
                # corrupt the token rather than protect it.
                csrf_header = f"""
                document.body.addEventListener('htmx:configRequest', function(evt) {{
                    evt.detail.headers['X-CSRF-Token'] = {js_string(ctx.csrf_token)};
                }});
                """

            parts.append(f"""
            <script>
                {csrf_header}
                document.body.addEventListener('htmx:afterSwap', function() {{
                    if (window.lucide) lucide.createIcons();
                }});
            </script>
            """)

        # Core admin JS (served from admin router's static mount).
        # Derived here rather than reused from render_head: that is a
        # separate method, so referencing its local raised NameError and
        # took down every page that reached this line.
        asset_prefix = ctx.base_url.rstrip("/") or "/admin"
        parts.append(
            f'<script src="{escape(asset_prefix)}/static/js/admin.js"></script>'
        )

        return "\n".join(parts)

    def get_body_attrs(self) -> dict[str, str]:
        """Get body tag attributes."""
        cfg = self.admin_config
        ctx = self.admin_context

        attrs = super().get_body_attrs()  # type: ignore[misc]

        classes = ["admin-layout"]
        if cfg.fixed_header:
            classes.append("fixed-header")
        if cfg.fixed_sidebar:
            classes.append("fixed-sidebar")
        if ctx.sidebar_collapsed:
            classes.append("sidebar-collapsed")

        attrs["class"] = " ".join(classes)

        return attrs


def admin_layout(
    content: str | Markup,
    config: AdminLayoutConfig,
    context: AdminLayoutContext,
) -> Markup:
    """Render the complete admin layout.

    Convenience function that creates AdminLayout and renders.

    Args:
        content: Page content to wrap
        config: Layout configuration
        context: Context (user, nav, etc.)

    Returns:
        Complete HTML page markup
    """
    layout = AdminLayout(config=config, context=context)
    return Markup(layout.render(str(content)))  # noqa: S704 — framework-composed trusted HTML


__all__ = [
    "AdminLayout",
    "AdminLayoutConfig",
    "AdminLayoutContext",
    "NavItemConfig",
    "admin_layout",
]
