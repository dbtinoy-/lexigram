"""
Table density management for header actions.

Handles table row density settings and user preferences.
"""

from __future__ import annotations

from collections.abc import Callable

from lexigram.admin.actions.header_manager.types import DensityConfig, TableDensity


class DensityManager:
    """Manages table density state and preferences."""

    def __init__(
        self,
        config: DensityConfig,
        storage: Callable[[str, str], None] | None = None,
        retriever: Callable[[str], str | None] | None = None,
    ) -> None:
        """Initialize the density manager.

        Args:
            config: Density configuration
            storage: Function to store preferences (key, value)
            retriever: Function to retrieve preferences (key) -> value
        """
        self.config = config
        self._storage = storage
        self._retriever = retriever
        self._current_density = config.default

        # Load saved preferences
        if config.save_preference and retriever:
            saved = retriever(config.storage_key)
            if saved:
                try:
                    self._current_density = TableDensity(saved)
                except ValueError:
                    self._current_density = config.default

    @property
    def current_density(self) -> TableDensity:
        """Get current density setting."""
        return self._current_density

    @property
    def available_options(self) -> list[TableDensity]:
        """Get available density options."""
        return self.config.options.copy()

    def set_density(self, density: TableDensity) -> None:
        """Set table density."""
        if density in self.config.options:
            self._current_density = density
            self._save_preferences()

    def cycle_density(self) -> TableDensity:
        """Cycle to next density option."""
        current_index = self.config.options.index(self._current_density)
        next_index = (current_index + 1) % len(self.config.options)
        next_density = self.config.options[next_index]
        self.set_density(next_density)
        return next_density

    def reset_to_default(self) -> None:
        """Reset to default density."""
        self._current_density = self.config.default
        self._save_preferences()

    def _save_preferences(self) -> None:
        """Save current preferences."""
        if self.config.save_preference and self._storage:
            self._storage(self.config.storage_key, self._current_density.value)

    def get_css_class(self) -> str:
        """Get CSS class for current density."""
        return f"table-density-{self._current_density.value}"

    def get_row_height(self) -> str:
        """Get row height for current density."""
        heights = {
            TableDensity.COMPACT: "32px",
            TableDensity.NORMAL: "48px",
            TableDensity.COMFORTABLE: "64px",
        }
        return heights.get(self._current_density, "48px")

    def get_font_size(self) -> str:
        """Get font size for current density."""
        sizes = {
            TableDensity.COMPACT: "0.875rem",
            TableDensity.NORMAL: "1rem",
            TableDensity.COMFORTABLE: "1.125rem",
        }
        return sizes.get(self._current_density, "1rem")
