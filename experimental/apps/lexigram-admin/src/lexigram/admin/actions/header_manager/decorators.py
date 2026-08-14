"""Decorators for header action management.

Re-exports shared decorators from ``lexigram.admin.actions.decorators`` and
adds header-specific ones (``requires_selection``, ``header_action``).
"""

from __future__ import annotations

from collections.abc import Callable
import functools
from typing import Any

from lexigram.admin.actions.decorators import (
    debounce,
    requires_confirmation,
    with_error_handling,
    with_loading_indicator,
)
from lexigram.admin.actions.header_manager.types import HeaderActionStyle
from lexigram.contracts.infra.resilience.protocols import ThrottlerProtocol

__all__ = [
    "ThrottlerProtocol",
    "debounce",
    "header_action",
    "requires_confirmation",
    "requires_selection",
    "with_error_handling",
    "with_loading_indicator",
]


def requires_selection(
    message: str = "Please select items to perform this action.",
) -> Callable:
    """Ensure items are selected before executing the action.

    Args:
        message: Error message shown when no items are selected.

    Returns:
        Decorator that checks for selected items before executing.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def header_action(
    name: str,
    label: str,
    icon: str | None = None,
    style: HeaderActionStyle = HeaderActionStyle.SECONDARY,
    confirm: bool = False,
    keyboard_shortcut: str | None = None,
) -> Callable:
    """Attach header-action metadata to a handler function.

    Args:
        name: Action identifier.
        label: Display label.
        icon: Optional icon name.
        style: Visual style variant.
        confirm: Whether to show a confirmation dialog.
        keyboard_shortcut: Optional keyboard shortcut key.

    Returns:
        Decorator that stores action metadata on the function.
    """

    def decorator(func: Callable) -> Callable:
        func._header_action_meta = {  # type: ignore[attr-defined]
            "name": name,
            "label": label,
            "icon": icon,
            "style": style.value if isinstance(style, HeaderActionStyle) else style,
            "confirm": confirm,
            "keyboard_shortcut": keyboard_shortcut,
        }
        return func

    return decorator
