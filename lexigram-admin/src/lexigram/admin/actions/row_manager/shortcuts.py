"""
Keyboard shortcuts management for row actions.

Handles keyboard shortcut registration and execution for row actions.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.actions.row_manager.types import RowAction
from lexigram.admin.actions.shortcuts import KeyboardShortcutManager as _Base


class KeyboardShortcutManager(_Base[RowAction]):
    """Manages keyboard shortcuts for row actions."""

    def execute_shortcut(
        self,
        shortcut: str,
        record_id: Any,
        record: Any | None = None,
    ) -> RowAction | None:
        """Return the action for *shortcut* if it can execute for *record*."""
        action = self._shortcuts.get(shortcut)
        if action and record and action.visible(record) and not action.disabled(record):
            return action
        return None

    def get_registered_shortcuts_with_labels(self) -> dict[str, str]:
        """Return a mapping of shortcut → action label."""
        return {sc: action.label for sc, action in self._shortcuts.items()}
