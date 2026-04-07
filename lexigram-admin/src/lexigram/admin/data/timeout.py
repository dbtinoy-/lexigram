from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

T = TypeVar("T")


class AdminQueryTimeoutError(TimeoutError):
    """Admin data operation exceeded the configured timeout."""


async def with_query_timeout(
    awaitable: Awaitable[T],
    *,
    timeout_seconds: float,
    operation: str,
) -> T:
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_seconds)
    except TimeoutError as exc:
        raise AdminQueryTimeoutError(
            f"admin query timed out after {timeout_seconds}s: {operation}"
        ) from exc
