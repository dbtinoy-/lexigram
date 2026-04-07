"""Timeout pattern implementation."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from lexigram.contracts.infra.resilience.models import TimeoutConfig
from lexigram.logging import get_logger
from lexigram.resilience.exceptions import ResilienceTimeoutError

logger = get_logger(__name__)


@asynccontextmanager
async def timeout_context(config: TimeoutConfig) -> AsyncGenerator[None, None]:
    """Context manager for timeout handling."""
    try:
        # Use asyncio.sleep(0) as a placeholder that completes immediately
        # The actual timeout is handled by the caller using asyncio.wait_for
        yield
    except TimeoutError as e:
        # Transform built-in TimeoutError to ResilienceTimeoutError
        if not isinstance(e, ResilienceTimeoutError):
            # Built-in TimeoutError - transform it
            raise ResilienceTimeoutError(
                f"Operation timed out: {e}",
                cause=e,
            ) from e
        else:
            # Already a ResilienceTimeoutError
            logger.warning(
                "Operation timed out",
                extra={"extra_data": {"timeout": config.timeout}},
            )
            raise


__all__ = [
    "ResilienceTimeoutError",
    "TimeoutConfig",
    "timeout_context",
]
