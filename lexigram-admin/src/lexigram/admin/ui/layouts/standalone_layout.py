"""Standalone Layout - Layout for pages without sidebar.

Used for login, error, and other standalone pages that don't
need the full admin chrome.
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
    ServerToastChannel,
    ToastConfig,
    flash_to_toast,
)
from lexigram.ui import BaseLayoutConfig, LayoutBase


@dataclass
class StandaloneLayoutConfig(BaseLayoutConfig):
    """Configuration for standalone layout."""

    # Branding
    app_name: str = "Admin"
    app_logo: str | None = None
    app_logo_alt: str = "Logo"

    # Features
    show_footer: bool = True
    show_logo: bool = True
    centered: bool = True

    # Background
    background_class: str = "bg-muted dark:bg-background"


@dataclass
class StandaloneLayoutContext:
    """Context for standalone layout."""

    # Page
    page_title: str = ""
    page_description: str | None = None

    # URLs
    base_url: str = "/admin"
    login_url: str = "/admin/login"

    # Messages
    flash_messages: list[tuple[str, str]] = field(default_factory=list)

    # Extra
    extra_head: str = ""
    extra_body_end: str = ""


class StandaloneLayout(LayoutBase):
    """Standalone layout without sidebar.

    Used for login pages, error pages, and other standalone views.
    """

    def __init__(
        self,
        config: StandaloneLayoutConfig | None = None,
        context: StandaloneLayoutContext | None = None,
    ):
        """Initialize standalone layout.

        Args:
            config: Layout configuration
            context: Layout context
        """
        self.standalone_config = config or StandaloneLayoutConfig()
        self.standalone_context = context or StandaloneLayoutContext()

        # Initialize base
        super().__init__(self.standalone_config)

        # Set up components
        self._setup_components()

    def _setup_components(self) -> None:
        """Set up layout components."""
        cfg = self.standalone_config

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
                position="top-center",
            ),
        )

    def render_head_content(self, **kwargs: Any) -> str:
        """Render additional head content."""
        cfg = self.standalone_config
        ctx = self.standalone_context

        parts: list[str] = []

        # Title
        if ctx.page_title:
            parts.append(
                f"<title>{escape(ctx.page_title)} | {escape(cfg.app_name)}</title>",
            )
        else:
            parts.append(f"<title>{escape(cfg.app_name)}</title>")

        if ctx.page_description:
            parts.append(
                f'<meta name="description" content="{escape(ctx.page_description)}">',
            )

        # Tailwind CSS via static build (utility classes for layout)
        parts.append('<link rel="stylesheet" href="/admin/static/css/tailwind.css">')
        parts.append(DARK_BOOTSTRAP_SCRIPT)
        parts.append(THEME_BRIDGE_SCRIPT)

        # Lucide icons
        parts.append('<script src="https://unpkg.com/lucide@latest"></script>')

        # Extra head content
        if ctx.extra_head:
            parts.append(ctx.extra_head)

        return "\n".join(parts)

    def render_body_content(self, content: str = "", **kwargs: Any) -> str:
        """Render body content.

        Args:
            content: Main content

        Returns:
            Body inner HTML
        """
        cfg = self.standalone_config
        ctx = self.standalone_context

        parts: list[str] = []

        # Container
        centered_class = "min-h-screen flex flex-col" if cfg.centered else ""
        parts.append(
            f'<div class="standalone-wrapper {cfg.background_class} {centered_class}">',
        )

        # Header with logo
        if cfg.show_logo:
            parts.append(self._render_header())

        # Main content
        main_class = (
            "flex-1 flex items-center justify-center w-full"
            if cfg.centered
            else "w-full"
        )
        parts.append(f'<main class="standalone-content {main_class}">')
        parts.append(content)
        parts.append("</main>")

        # Footer
        if cfg.show_footer:
            parts.append(self.footer_renderer.render())

        parts.append("</div>")

        # Toasts
        toasts = flash_to_toast(ctx.flash_messages)
        parts.append(self.toast_renderer.render_container(toasts))

        # Init icons
        parts.append("""
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                if (window.lucide) lucide.createIcons();
            });
        </script>
        """)

        # Extra body end
        if ctx.extra_body_end:
            parts.append(ctx.extra_body_end)

        return "\n".join(parts)

    def _render_header(self) -> str:
        """Render simple header with logo."""
        cfg = self.standalone_config
        ctx = self.standalone_context

        parts: list[str] = []

        parts.append('<header class="standalone-header py-2 text-center">')
        parts.append(
            f'<a href="{escape(ctx.base_url)}" class="inline-flex items-center gap-2">',
        )

        if cfg.app_logo:
            parts.append(
                f'<img src="{escape(cfg.app_logo)}" alt="{escape(cfg.app_logo_alt)}" class="h-10">',
            )
        else:
            parts.append(
                f'<span class="text-2xl font-bold text-foreground">{escape(cfg.app_name)}</span>',
            )

        parts.append("</a>")
        parts.append("</header>")

        return "\n".join(parts)

    def get_body_attrs(self) -> dict[str, str]:
        """Get body attributes."""
        attrs = super().get_body_attrs()  # type: ignore[misc]
        attrs["class"] = "standalone-layout"
        return attrs


def standalone_layout(
    content: str | Markup,
    config: StandaloneLayoutConfig | None = None,
    context: StandaloneLayoutContext | None = None,
) -> Markup:
    """Render a standalone layout.

    Convenience function for standalone pages.

    Args:
        content: Page content
        config: Layout configuration
        context: Layout context

    Returns:
        Complete HTML page
    """
    layout = StandaloneLayout(config=config, context=context)
    return Markup(layout.render(str(content)))


__all__ = [
    "StandaloneLayout",
    "StandaloneLayoutConfig",
    "StandaloneLayoutContext",
    "standalone_layout",
]
