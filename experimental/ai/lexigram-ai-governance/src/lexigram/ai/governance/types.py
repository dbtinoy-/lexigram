"""Type definitions for AI Governance."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

# Callback type for soft-limit notifications.
# Signature: ``async def cb(user_id, current_spend, budget) -> None``
SoftLimitCallback = Callable[
    [str | None, float, float],
    Coroutine[Any, Any, None] | None,
]


__all__ = [
    "SoftLimitCallback",
]
