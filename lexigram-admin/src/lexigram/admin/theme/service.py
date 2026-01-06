from __future__ import annotations

from lexigram.ui.styles.theme import shadcn_css


class AdminThemeService:
    """Generates and caches theme CSS from a configurable primary color.

    Args:
        primary_color: Hex color string.
    """

    def __init__(self, primary_color: str = "#6b7280") -> None:
        self._primary_color = primary_color
        self._cached_css: str | None = None

    def generate_theme_css(self) -> str:
        """Return the full theme CSS, cached until the color changes."""
        if self._cached_css is None:
            self._cached_css = shadcn_css(primary=self._primary_color)
        return self._cached_css

    def update_primary_color(self, color: str) -> None:
        """Update the primary color and invalidate the CSS cache."""
        self._primary_color = color
        self._cached_css = None
