"""Consumer-facing decorators for webhook event registration."""

from __future__ import annotations

from collections.abc import Callable
import functools
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def webhook_event(
    event_type: str,
    *,
    description: str = "",
) -> Callable[[F], F]:
    """Mark an async function as a webhook event emitter.

    Attaches webhook metadata that the webhook bridge or middleware can
    read to automatically dispatch ``WebhookEvent`` instances on successful
    execution.

    Args:
        event_type: Dot-notation event type (e.g. ``"order.created"``).
        description: Human-readable description of the event.

    Returns:
        Decorator that attaches webhook metadata to the function.

    Example::

        @webhook_event("order.created", description="Fired when a new order is placed")
        async def create_order(self, data: dict) -> Order:
            ...
    """

    def decorator(fn: F) -> F:
        fn.__webhook_event__ = True  # type: ignore[attr-defined]
        fn.__webhook_event_type__ = event_type  # type: ignore[attr-defined]
        fn.__webhook_event_description__ = description  # type: ignore[attr-defined]

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


__all__ = ["webhook_event"]
