"""Retry policy for HTTP client requests.

Local implementation to avoid cross-package imports from lexigram.resilience.
"""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING, Any

from lexigram.contracts.infra.resilience.models import RetryConfig

if TYPE_CHECKING:
    from collections.abc import Callable


def _calculate_delay(
    attempt: int,
    config: RetryConfig,
    base_delay: float = 0.0,
) -> float:
    """Calculate delay with exponential backoff and optional jitter.

    Args:
        attempt: Zero-based attempt index.
        config: Retry configuration.
        base_delay: Base delay in seconds before applying backoff.

    Returns:
        Computed delay capped at ``config.max_delay``.
    """
    delay = base_delay * (config.backoff_factor**attempt)
    if config.jitter:
        jitter_range = config.jitter if isinstance(config.jitter, float) else 0.5
        delay = delay * (1 + random.uniform(-jitter_range, jitter_range))  # noqa: S311 — retry jitter (non-crypto)
    return min(delay, config.max_delay)


_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _method_is_idempotent(method: str | None) -> bool:
    """Return whether *method* is idempotent under the default retry policy.

    Args:
        method: HTTP method, or None for non-HTTP callers.

    Returns:
        True for ``GET``/``HEAD``/``OPTIONS`` (case-insensitive) and for
        None (non-HTTP callers — gate inactive); False for all other methods.
    """
    if method is None:
        return True
    return method.upper() in _IDEMPOTENT_METHODS


class RetryPolicy:
    """Retry policy for HTTP client requests.

    Executes an async callable with configurable retry logic, exponential
    backoff, and per-exception filtering.

    Args:
        config: Retry configuration controlling max retries, delays, and
            which exceptions trigger a retry.
    """

    def __init__(self, config: RetryConfig | None = None) -> None:
        self.config = config or RetryConfig()

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        method: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute an async function with retries.

        Args:
            func: Async callable to execute.
            *args: Positional arguments forwarded to *func*.
            method: The HTTP method of the request, used only for the
                idempotency gate (never forwarded to *func*). When ``None``
                (non-HTTP callers) the gate is inactive.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            The return value of *func* on success.

        Raises:
            Exception: The last exception raised when all retries are exhausted.
        """
        last_exception: Exception | None = None

        for attempt in range(self.config.max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:  # noqa: BLE001 — retry policy must capture any exception to evaluate retry_on config
                last_exception = e
                should_retry = isinstance(e, self.config.retry_on) or (
                    self.config.retry_if and self.config.retry_if(e)
                )
                if (
                    should_retry
                    and self.config.idempotent_methods_only
                    and not _method_is_idempotent(method)
                ):
                    should_retry = False
                if not should_retry:
                    raise
                if attempt < self.config.max_attempts:
                    delay = _calculate_delay(
                        attempt, self.config, self.config.base_delay
                    )
                    await asyncio.sleep(delay)

        raise last_exception  # type: ignore[misc]


__all__ = ["RetryPolicy"]
