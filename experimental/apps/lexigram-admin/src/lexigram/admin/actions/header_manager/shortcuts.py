"""
Keyboard shortcuts management for header actions.

Handles keyboard shortcut registration and execution.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.actions.header_manager.types import HeaderAction
from lexigram.admin.actions.shortcuts import KeyboardShortcutManager as _Base


class KeyboardShortcutManager(_Base[HeaderAction]):
    """Manages keyboard shortcuts for header actions.

    Actions are stored in the core ``Registry`` owned by the base manager;
    execution derives the handler from the registered action so there is a
    single source of truth for a shortcut's binding.
    """

    def execute_shortcut(self, shortcut: str) -> Any:
        """Execute the handler registered for *shortcut*."""
        action = self.get_action_for_shortcut(shortcut)
        if action and action.handler:
            return action.handler()
        return None
