"""Head section renderer.

Renders the HTML head section with CSS and meta tags.
"""

from __future__ import annotations

from markupsafe import escape

from lexigram.ui.config import HeadConfig


class HeadRenderer:
    """Renders the head section content."""

    CSS_FRAMEWORKS = {
        "tailwind": "https://cdn.tailwindcss.com",
        "pico": "https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css",
    }

    def __init__(self, config: HeadConfig | None = None):
        """Initialize the renderer.

        Args:
            config: Head configuration
        """
        self.config = config or HeadConfig()

    def render(self, extra_css: str = "") -> str:
        """Render the head content.

        Args:
            extra_css: Additional inline CSS to include

        Returns:
            HTML string for head section
        """
        parts: list[str] = []

        # CSS Framework
        parts.append(self._render_css_framework())

        # Font
        if self.config.font_url:
            parts.append('<link rel="preconnect" href="https://fonts.googleapis.com">')
            parts.append(
                f'<link rel="stylesheet" href="{escape(self.config.font_url)}">',
            )

        # Icon library
        parts.append(self._render_icon_library())

        # Custom CSS files
        for css_file in self.config.css_files:
            parts.append(f'<link rel="stylesheet" href="{escape(css_file)}">')

        # HTMX
        parts.append(f'<script src="{escape(self.config.htmx_url)}"></script>')

        # Hyperscript
        if self.config.include_hyperscript:
            parts.append(
                f'<script src="{escape(self.config.hyperscript_url)}"></script>',
            )

        # Inline CSS
        if self.config.inline_css or extra_css:
            parts.append("<style>")
            if self.config.inline_css:
                parts.append(self.config.inline_css)
            if extra_css:
                parts.append(extra_css)
            parts.append("</style>")

        return "\n".join(parts)

    def _render_css_framework(self) -> str:
        """Render CSS framework link."""
        if self.config.css_framework_url:
            url = self.config.css_framework_url
        else:
            url = self.CSS_FRAMEWORKS.get(self.config.css_framework, "")

        if not url:
            return ""

        if self.config.css_framework == "tailwind":
            return f'<script src="{escape(url)}"></script>'
        return f'<link rel="stylesheet" href="{escape(url)}">'

    def _render_icon_library(self) -> str:
        """Render icon library script."""
        if self.config.icon_library == "lucide" and self.config.icon_library_url:
            return f"""
<script src="{escape(self.config.icon_library_url)}"></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {{
        if (window.lucide) lucide.createIcons();
    }});
</script>"""
        return ""


__all__ = ["HeadConfig", "HeadRenderer"]
