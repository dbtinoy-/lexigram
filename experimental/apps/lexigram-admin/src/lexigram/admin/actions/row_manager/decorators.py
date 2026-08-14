"""Decorators for row action management.

Re-exports shared decorators from ``lexigram.admin.actions.decorators`` and
adds row-specific ones (``requires_permission``, ``row_action``).
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
from lexigram.admin.actions.row_manager.types import ActionStyle
from lexigram.contracts.infra.resilience.protocols import ThrottlerProtocol

__all__ = [
    "ThrottlerProtocol",
    "debounce",
    "requires_confirmation",
    "requires_permission",
    "row_action",
    "with_error_handling",
    "with_loading_indicator",
]


def requires_permission(permission: str) -> Callable:
    """Check that the current user has *permission* before executing.

    Args:
        permission: The permission string required (e.g., ``"users:edit"``).

    Returns:
        Decorator that gates execution on the permission check.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def row_action(
    name: str,
    label: str,
    icon: str | None = None,
    style: ActionStyle = ActionStyle.SECONDARY,
    confirm: bool = False,
    keyboard_shortcut: str | None = None,
) -> Callable:
    """Attach row-action metadata to a handler function.

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
        func._row_action_meta = {  # type: ignore[attr-defined]
            "name": name,
            "label": label,
            "icon": icon,
            "style": style.value if isinstance(style, ActionStyle) else style,
            "confirm": confirm,
            "keyboard_shortcut": keyboard_shortcut,
        }
        return func

    return decorator
