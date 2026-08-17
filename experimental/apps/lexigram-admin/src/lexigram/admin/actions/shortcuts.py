"""Generic keyboard shortcut manager for action types.

Provides a reusable :class:`KeyboardShortcutManager` that works with any
action type that has ``keyboard_shortcut`` and ``name`` attributes.
"""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar


class _HasShortcut(Protocol):
    """Minimal protocol for actions that support keyboard shortcuts."""

    keyboard_shortcut: str | None
    name: str


ActionT = TypeVar("ActionT", bound=_HasShortcut)


class KeyboardShortcutManager(Generic[ActionT]):
    """Manages keyboard shortcuts for any action type.

    Handles shortcut registration, lookup, and formatting.  Sub-managers
    extend this class to add type-specific execution logic (e.g., passing
    a ``record_id`` for row actions).
    """

    def __init__(self) -> None:
        """Initialize the shortcut manager."""
        self._shortcuts: dict[str, ActionT] = {}

    def register_action(self, action: ActionT) -> None:
        """Register an action under its keyboard shortcut."""
        if action.keyboard_shortcut:
            self._shortcuts[action.keyboard_shortcut] = action

    def unregister_action(self, shortcut: str) -> None:
        """Remove a shortcut registration."""
        self._shortcuts.pop(shortcut, None)

    def get_action_for_shortcut(self, shortcut: str) -> ActionT | None:
        """Return the action bound to *shortcut*, or ``None``."""
        return self._shortcuts.get(shortcut)

    def get_registered_shortcuts(self) -> dict[str, str]:
        """Return a mapping of shortcut → action name."""
        return {sc: action.name for sc, action in self._shortcuts.items()}

    def is_shortcut_registered(self, shortcut: str) -> bool:
        """Return ``True`` if *shortcut* is currently registered."""
        return shortcut in self._shortcuts

    def clear_all_shortcuts(self) -> None:
        """Remove all registered shortcuts."""
        self._shortcuts.clear()

    @staticmethod
    def normalize_shortcut(shortcut: str) -> str:
        """Normalise a shortcut string to lowercase with no spaces.

        Examples:
            ``'Ctrl+R'`` → ``'ctrl+r'``
        """
        return shortcut.lower().replace(" ", "")

    @staticmethod
    def format_shortcut(shortcut: str) -> str:
        """Format a normalised shortcut for display.

        Examples:
            ``'ctrl+r'`` → ``'Ctrl+R'``
            ``'delete'`` → ``'Del'``
        """
        _SPECIAL = {
            "ctrl": "Ctrl",
            "cmd": "Cmd",
            "alt": "Alt",
            "shift": "Shift",
            "delete": "Del",
        }
        parts = shortcut.split("+")
        return "+".join(_SPECIAL.get(p, p.upper()) for p in parts)
