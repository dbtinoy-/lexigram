"""Base layout class for lexigram-admin.

Provides the foundation for all admin layouts with common functionality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from markupsafe import Markup, escape

from lexigram.ui.config import BaseLayoutConfig
from lexigram.ui.layouts.html_document import (
    HTMLDocument,
)
from lexigram.ui.layouts.mixins import (
    CSSManager,
    JSManager,
)


@dataclass
class BaseLayoutContext:
    """Base context for all layouts.

    Common context data used across layouts.
    """

    # Page info
    title: str = ""
    description: str = ""

    # Current user (if authenticated)
    user_name: str | None = None
    user_email: str | None = None
    user_avatar: str | None = None
    user_role: str | None = None

    # URLs
    base_url: str = "/admin"
    logout_url: str = "/admin/logout"
    login_url: str = "/admin/login"

    # Flash messages
    flash_messages: list[tuple[str, str]] = field(default_factory=list)

    # CSRF
    csrf_token: str | None = None

    # Custom data
    extra: dict[str, Any] = field(default_factory=dict)


class LayoutBase(HTMLDocument):
    """Base layout class for all admin layouts.

    Combines HTMLDocument with CSS, JS, HTMX, and theming via composition.
    Subclasses should implement render_body_content() and optionally override
    other methods for customization.

    Example:
        class MyLayout(LayoutBase):
            def render_body_content(self, content: str = "", **context) -> str:
                return f'<main>{content}</main>'
    """

    def __init__(
        self,
        config: BaseLayoutConfig | None = None,
        context: BaseLayoutContext | None = None,
    ):
        """Initialize the layout.

        Args:
            config: Layout configuration
            context: Layout context
        """
        # Initialize parent document
        resolved_config = config or BaseLayoutConfig()
        super().__init__(config=resolved_config)

        # Initialize asset managers via composition
        self._css = CSSManager()
        self._js = JSManager()

        # Store typed config and context
        self.layout_config: BaseLayoutConfig = resolved_config
        self.context = context or BaseLayoutContext()

        # Theme attributes
        self.theme: str = self.layout_config.theme
        self.primary_color: str = self.layout_config.primary_color

        # HTMX attributes
        self.htmx_enabled: bool = self.layout_config.htmx_enabled
        self.htmx_boost: bool = self.layout_config.htmx_boost
        self.htmx_version: str = self.layout_config.htmx_version
        self.htmx_indicator: str = ".htmx-indicator"

        # Setup default CSS/JS
        self._setup_defaults()

    def _setup_defaults(self) -> None:
        """Setup default CSS and JS files."""
        # Add configured CSS files
        for css_file in self.layout_config.css_files:
            self._css.add_css(css_file)

        # Add configured JS files
        for js_file in self.layout_config.js_files:
            self._js.add_js(js_file, defer=True)

    # CSS delegation methods
    def add_css(self, href: str, **attrs: str) -> None:
        """Add a CSS file link.

        Args:
            href: URL to CSS file
            **attrs: Additional attributes (media, crossorigin, etc.)
        """
        self._css.add_css(href, **attrs)

    def add_inline_style(self, css: str) -> None:
        """Add inline CSS.

        Args:
            css: CSS rules
        """
        self._css.add_inline_style(css)

    def render_css(self) -> str:
        """Render all CSS as HTML.

        Returns:
            HTML string with link and style tags
        """
        return self._css.render_css()

    # JS delegation methods
    def add_js(
        self,
        src: str,
        defer: bool = False,
        async_: bool = False,
        **attrs: str,
    ) -> None:
        """Add a JavaScript file.

        Args:
            src: URL to JS file
            defer: Add defer attribute
            async_: Add async attribute
            **attrs: Additional attributes
        """
        self._js.add_js(src, defer=defer, async_=async_, **attrs)

    def add_inline_script(self, script: str, defer: bool = False) -> None:
        """Add inline JavaScript.

        Args:
            script: JavaScript code
            defer: If True, render at end of body
        """
        self._js.add_inline_script(script, defer=defer)

    def render_js_head(self) -> str:
        """Render JS for head section.

        Returns:
            HTML string with script tags
        """
        return self._js.render_js_head()

    def render_js_body_end(self) -> str:
        """Render deferred JS for end of body.

        Returns:
            HTML string with script tags
        """
        return self._js.render_js_body_end()

    # HTMX methods (inlined from HTMXMixin)
    def get_htmx_config(self) -> dict[str, Any]:
        """Get HTMX configuration.

        Returns:
            Configuration dict for htmx.config
        """
        return {
            "historyCacheSize": 10,
            "refreshOnHistoryMiss": True,
            "defaultSwapStyle": "innerHTML",
            "defaultSwapDelay": 0,
            "defaultSettleDelay": 20,
            "includeIndicatorStyles": True,
            "indicatorClass": "htmx-indicator",
            "requestClass": "htmx-request",
            "addedClass": "htmx-added",
            "swappingClass": "htmx-swapping",
            "settlingClass": "htmx-settling",
        }

    def render_htmx_head(self) -> str:
        """Render HTMX script tag for head.

        Returns:
            HTML string with HTMX script
        """
        if not self.htmx_enabled:
            return ""

        return f'<script src="https://unpkg.com/htmx.org@{self.htmx_version}"></script>'

    def get_htmx_body_attrs(self) -> str:
        """Get HTMX-related body attributes.

        Returns:
            String of HTML attributes
        """
        if not self.htmx_enabled:
            return ""

        attrs = []
        if self.htmx_boost:
            attrs.append('hx-boost="true"')
        if self.htmx_indicator:
            attrs.append(f'hx-indicator="{escape(self.htmx_indicator)}"')

        return " ".join(attrs)

    # Theme methods (inlined from ThemeMixin)
    def get_theme_css_variables(self) -> str:
        """Generate ShadCN-compatible CSS variable declarations."""
        from lexigram.ui.styles.design_tokens import render_all_tokens

        return render_all_tokens()

    def get_theme_html_attrs(self) -> str:
        """Get theme-related HTML element attributes.

        Returns:
            String of HTML attributes
        """
        return f'data-theme="{escape(self.theme)}"'

    def get_dark_mode_script(self) -> str:
        """Inline script that applies dark class before paint (prevents FOUC).

        Must run synchronously in ``<head>`` before any CSS paints.
        """
        return """
<script>
(function() {
    var theme = localStorage.getItem('theme');
    if (theme === 'dark' || ((!theme || theme === 'system') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
    }
})();
</script>"""

    def get_alpine_theme_data(self) -> str:
        """Register Alpine.js theme toggle component data."""
        return """
<script>
document.addEventListener('alpine:init', function() {
    Alpine.data('themeToggle', function() {
        return {
            theme: localStorage.getItem('theme') || 'system',
            init: function() {
                var val = this.theme;
                if (val === 'dark' || (val === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                    document.documentElement.classList.add('dark');
                }
                this.$watch('theme', function(val) {
                    localStorage.setItem('theme', val);
                    if (val === 'dark' || (val === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                        document.documentElement.classList.add('dark');
                    } else {
                        document.documentElement.classList.remove('dark');
                    }
                });
            },
            cycleTheme: function() {
                var modes = ['light', 'dark', 'system'];
                var idx = modes.indexOf(this.theme);
                this.theme = modes[(idx + 1) % modes.length];
            }
        };
    });
});
</script>"""

    def render(  # type: ignore[override]
        self,
        content: str | Markup = "",
        title: str | None = None,
        **extra_context: Any,
    ) -> Markup:
        """Render the complete layout.

        Args:
            content: Main page content
            title: Page title (overrides context title)
            **extra_context: Additional context

        Returns:
            Complete HTML document as Markup
        """
        # Use provided title or fall back to context
        page_title = title or self.context.title
        if page_title and self.layout_config.site_name:
            full_title = f"{page_title} - {self.layout_config.site_name}"
        else:
            full_title = page_title or self.layout_config.site_name

        # Merge extra context
        ctx = {
            "content": content,
            "context": self.context,
            **extra_context,
        }

        return super().render(title=full_title, **ctx)

    def get_body_attributes(self, **context: Any) -> str:
        """Get body element attributes including theme and HTMX."""
        attrs = []

        # Theme
        attrs.append(self.get_theme_html_attrs())

        # HTMX
        htmx_attrs = self.get_htmx_body_attrs()
        if htmx_attrs:
            attrs.append(htmx_attrs)

        return " ".join(filter(None, attrs))

    def render_head_content(self, **context: Any) -> str:
        """Render head content (CSS, theme, HTMX)."""
        parts: list[str] = []

        # Dark mode — apply before paint to prevent FOUC
        parts.append(self.get_dark_mode_script())

        # Theme CSS variables
        parts.append("<style>")
        parts.append(self.get_theme_css_variables())
        parts.append("</style>")

        # HTMX
        htmx_head = self.render_htmx_head()
        if htmx_head:
            parts.append(htmx_head)

        # Alpine.js if enabled
        if self.layout_config.include_alpine:
            parts.append(
                f'<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@{self.layout_config.alpine_version}/dist/cdn.min.js"></script>',
            )

        # External CSS
        css_html = self.render_css()
        if css_html:
            parts.append(css_html)

        # JS in head
        js_head = self.render_js_head()
        if js_head:
            parts.append(js_head)

        return "\n".join(parts)

    def render_body_content(self, content: str = "", **context: Any) -> str | Markup:
        """Render body content.

        Default implementation just returns content.
        Subclasses should override to add layout structure.

        Args:
            content: Main content
            **context: Additional context

        Returns:
            HTML string or Markup
        """
        return content

    def render_body_end(self, **context: Any) -> str:
        """Render content at end of body (deferred scripts)."""
        parts: list[str] = []

        # Flash messages as toast script
        if self.context.flash_messages:
            parts.append(self._render_flash_script())

        # Dark mode Alpine.js data
        parts.append(self.get_alpine_theme_data())

        # Deferred JS
        js_end = self.render_js_body_end()
        if js_end:
            parts.append(js_end)

        return "\n".join(parts)

    def _render_flash_script(self) -> str:
        """Render JavaScript to display flash messages as toasts."""
        if not self.context.flash_messages:
            return ""

        # Convert flash messages to JS
        messages = []
        for msg_type, message in self.context.flash_messages:
            messages.append(
                f'{{type: "{escape(msg_type)}", message: "{escape(message)}"}}',
            )

        return f"""
<script>
document.addEventListener('DOMContentLoaded', function() {{
    const messages = [{", ".join(messages)}];
    messages.forEach(function(m) {{
        if (window.showToast) {{
            window.showToast(m.message, m.type);
        }} else {{
            console.log('[' + m.type + ']', m.message);
        }}
    }});
}});
</script>
"""


__all__ = ["BaseLayoutConfig", "BaseLayoutContext", "LayoutBase"]
