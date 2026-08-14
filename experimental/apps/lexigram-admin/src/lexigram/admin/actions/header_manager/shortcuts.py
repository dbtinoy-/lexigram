"""
Keyboard shortcuts management for header actions.

Handles keyboard shortcut registration and execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.actions.header_manager.types import HeaderAction
from lexigram.admin.actions.shortcuts import KeyboardShortcutManager as _Base

if TYPE_CHECKING:
    from collections.abc import Callable


class KeyboardShortcutManager(_Base[HeaderAction]):
    """Manages keyboard shortcuts for header actions."""

    def __init__(self) -> None:
        """Initialize the shortcut manager."""
        super().__init__()
        self._handlers: dict[str, Callable[[], Any]] = {}

    def register_action(self, action: HeaderAction) -> None:
        """Register an action with its keyboard shortcut."""
        super().register_action(action)
        if action.keyboard_shortcut and action.handler:
            self._handlers[action.keyboard_shortcut] = action.handler

    def unregister_action(self, shortcut: str) -> None:
        """Unregister an action by its shortcut."""
        super().unregister_action(shortcut)
        self._handlers.pop(shortcut, None)

    def execute_shortcut(self, shortcut: str) -> Any:
        """Execute the handler registered for *shortcut*."""
        handler = self._handlers.get(shortcut)
        if handler:
            return handler()
        return None

    def clear_all_shortcuts(self) -> None:
        """Clear all registered shortcuts and handlers."""
        super().clear_all_shortcuts()
        self._handlers.clear()
