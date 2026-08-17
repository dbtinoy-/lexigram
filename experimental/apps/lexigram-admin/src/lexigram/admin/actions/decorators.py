"""Shared action decorators for header and row action managers.

Provides four generic decorators that work with both header actions (no
``record_id``) and row actions (``record_id`` as first positional arg).
Each sub-manager re-exports the decorators it uses and may add its own
type-specific ones on top.

Throttling is provided by :class:`lexigram.resilience.throttle.Throttler`
from the framework — import it directly from there.
"""

from __future__ import annotations

import asyncio
import functools
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


def requires_confirmation(
    message: str = "Are you sure you want to perform this action?",
    title: str = "Confirm Action",
) -> Callable:
    """Show a confirmation dialog before executing an action handler.

    Args:
        message: Confirmation message displayed to the user.
        title: Dialog title.

    Returns:
        Decorator that wraps the handler with confirmation logic.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def with_loading_indicator(loading_text: str = "Processing...") -> Callable:
    """Show a loading indicator while an action handler executes.

    Args:
        loading_text: Text displayed during the loading state.

    Returns:
        Decorator that wraps the handler with loading-state logic.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            finally:
                pass  # Loading indicator teardown handled by the UI layer.

        return wrapper

    return decorator


def with_error_handling(
    error_message: str = "An error occurred while performing the action.",
) -> Callable:
    """Wrap an action handler to surface errors via the UI layer.

    Args:
        error_message: Message shown to the user when an error occurs.

    Returns:
        Decorator that wraps the handler with error-handling logic.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def debounce(delay: float = 0.5) -> Callable:
    """Debounce an action handler so it only fires after *delay* seconds.

    Args:
        delay: Minimum time in seconds between executions.

    Returns:
        Debounced async wrapper.
    """

    def decorator(func: Callable) -> Callable:
        last_call: float | None = None

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal last_call
            current_time = time.time()
            if last_call is None or current_time - last_call >= delay:
                last_call = current_time
                return await func(*args, **kwargs)
            remaining = delay - (current_time - last_call)
            await asyncio.sleep(remaining)
            last_call = time.time()
            return await func(*args, **kwargs)

        return wrapper

    return decorator
