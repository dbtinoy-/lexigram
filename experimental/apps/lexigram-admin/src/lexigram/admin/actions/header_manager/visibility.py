"""
Column visibility management for header actions.

Handles showing/hiding table columns and saving user preferences.
"""

from __future__ import annotations

from collections.abc import Callable

from lexigram import serialization as json
from lexigram.admin.actions.header_manager.types import ColumnVisibilityConfig


class ColumnVisibilityManager:
    """Manages column visibility state and preferences."""

    def __init__(
        self,
        config: ColumnVisibilityConfig,
        storage: Callable[[str, str], None] | None = None,
        retriever: Callable[[str], str | None] | None = None,
    ) -> None:
        """Initialize the visibility manager.

        Args:
            config: Visibility configuration
            storage: Function to store preferences (key, value)
            retriever: Function to retrieve preferences (key) -> value
        """
        self.config = config
        self._storage = storage
        self._retriever = retriever
        self._visible_columns: set[str] = set()

        # Load saved preferences
        if config.save_preference and retriever:
            saved = retriever(config.storage_key)
            if saved:
                try:
                    self._visible_columns = set(json.loads(saved))
                except (json.JSONDecodeError, TypeError):
                    self._visible_columns = set(config.default_visible)

        # Initialize with defaults if no saved preferences
        if not self._visible_columns:
            self._visible_columns = set(config.default_visible)

    @property
    def visible_columns(self) -> set[str]:
        """Get currently visible columns."""
        return self._visible_columns.copy()

    def is_column_visible(self, column: str) -> bool:
        """Check if a column is visible."""
        if column in self.config.always_visible:
            return True
        return column in self._visible_columns

    def show_column(self, column: str) -> None:
        """Show a column."""
        if column not in self.config.always_visible:
            self._visible_columns.add(column)
            self._save_preferences()

    def hide_column(self, column: str) -> None:
        """Hide a column."""
        if column not in self.config.always_visible:
            self._visible_columns.discard(column)
            self._save_preferences()

    def toggle_column(self, column: str) -> None:
        """Toggle column visibility."""
        if self.is_column_visible(column):
            self.hide_column(column)
        else:
            self.show_column(column)

    def show_all_columns(self, all_columns: list[str]) -> None:
        """Show all columns."""
        for column in all_columns:
            if column not in self.config.always_visible:
                self._visible_columns.add(column)
        self._save_preferences()

    def hide_all_columns(self) -> None:
        """Hide all columns except always visible ones."""
        self._visible_columns = set(self.config.always_visible)
        self._save_preferences()

    def reset_to_defaults(self, all_columns: list[str] | None = None) -> None:
        """Reset to default visibility."""
        self._visible_columns = set(self.config.default_visible)
        if all_columns:
            # Ensure always visible columns are included
            self._visible_columns.update(self.config.always_visible)
        self._save_preferences()

    def _save_preferences(self) -> None:
        """Save current preferences."""
        if self.config.save_preference and self._storage:
            visible_list = list(self._visible_columns)
            self._storage(self.config.storage_key, json.dumps(visible_list))  # type: ignore[arg-type]

    def get_hidden_columns(self, all_columns: list[str]) -> list[str]:
        """Get list of hidden columns."""
        return [col for col in all_columns if not self.is_column_visible(col)]

    def get_visible_columns_list(self, all_columns: list[str]) -> list[str]:
        """Get list of visible columns in original order."""
        return [col for col in all_columns if self.is_column_visible(col)]
