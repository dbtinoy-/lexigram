"""Footer component for admin layout.

Renders the page footer with copyright, links, and version info.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from markupsafe import escape

from lexigram.ui.config import FooterConfig


@dataclass
class FooterLink:
    """A footer link."""

    label: str
    url: str
    target: str = "_self"
    icon: str | None = None


class FooterRenderer:
    """Renders the admin footer."""

    def __init__(self, config: FooterConfig | None = None):
        """Initialize the renderer.

        Args:
            config: Footer configuration
        """
        self.config = config or FooterConfig()

    def render(self) -> str:
        """Render the footer.

        Returns:
            HTML string for footer
        """
        parts: list[str] = []

        sticky_class = "footer-sticky" if self.config.sticky else ""
        divider_class = "footer-divider" if self.config.show_divider else ""

        parts.append(f'<footer class="admin-footer {sticky_class} {divider_class}">')
        parts.append('<div class="footer-content">')

        # Left section
        parts.append('<div class="footer-left">')

        if self.config.custom_left:
            parts.append(self.config.custom_left)
        elif self.config.show_copyright:
            parts.append(self._render_copyright())

        parts.append("</div>")

        # Center section (links)
        if self.config.links:
            parts.append(self._render_links())

        # Right section
        parts.append('<div class="footer-right">')

        if self.config.custom_right:
            parts.append(self.config.custom_right)
        elif self.config.show_version and self.config.version:
            parts.append(
                f'<span class="footer-version">v{escape(self.config.version)}</span>',
            )

        parts.append("</div>")

        parts.append("</div>")
        parts.append("</footer>")

        return "\n".join(parts)

    def _render_copyright(self) -> str:
        """Render copyright text."""
        current_year = datetime.now().year

        if (
            self.config.copyright_start_year
            and self.config.copyright_start_year < current_year
        ):
            year_str = f"{self.config.copyright_start_year}-{current_year}"
        else:
            year_str = str(current_year)

        holder = self.config.copyright_holder or "All rights reserved"

        return (
            f'<span class="footer-copyright">&copy; {year_str} {escape(holder)}</span>'
        )

    def _render_links(self) -> str:
        """Render footer links."""
        parts: list[str] = []

        parts.append('<nav class="footer-links">')

        for link in self.config.links:
            icon = ""
            if link.icon:
                icon = f'<i data-lucide="{escape(link.icon)}" class="w-4 h-4"></i> '

            parts.append(f"""
            <a href="{escape(link.url)}"
               target="{escape(link.target)}"
               class="footer-link">
                {icon}{escape(link.label)}
            </a>
            """)

        parts.append("</nav>")

        return "\n".join(parts)


__all__ = ["FooterConfig", "FooterLink", "FooterRenderer"]
