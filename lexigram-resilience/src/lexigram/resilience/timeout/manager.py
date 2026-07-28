"""Named timeout registry for the resilience subsystem.

Provides :class:`TimeoutManager`, a lightweight registry that maps operation
names to per-operation timeout durations.  All operations are run under
``asyncio.wait_for``; a :class:`~lexigram.exceptions.ResilienceTimeoutError`
is raised if the coroutine does not complete within the configured budget.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TypeVar

from lexigram.logging import get_logger
from lexigram.resilience.exceptions import ResilienceTimeoutError

if TYPE_CHECKING:
    from collections.abc import Awaitable

T = TypeVar("T")

logger = get_logger(__name__)

_UNSET = object()  # sentinel for "no override"


class TimeoutManager:
    """Named timeout registry with per-operation configuration.

    A central registry that maps operation names to timeout durations.
    Unknown operations fall back to the *default* timeout.  Use
    :meth:`configure` to set per-operation overrides before running
    operations.

    Example::

        manager = TimeoutManager(default_seconds=10.0)
        manager.configure("send_email", seconds=5.0)
        manager.configure("run_report", seconds=120.0)

        result = await manager.run("send_email", send_email(user))
    """

    def __init__(self, default_seconds: float = 30.0) -> None:
        """Initialise the manager with a default timeout.

        Args:
            default_seconds: Fallback timeout (in seconds) applied to any
                operation that has not been given an explicit override.
                Must be positive.

        Raises:
            ValueError: If *default_seconds* is not positive.
        """
        if default_seconds <= 0:
            raise ValueError(
                f"default_seconds must be positive, got {default_seconds!r}"
            )
        self._default = default_seconds
        self._timeouts: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure(self, operation: str, seconds: float) -> None:
        """Register a per-operation timeout override.

        Args:
            operation: A string key identifying the operation.
            seconds: Timeout duration in seconds.  Must be positive.

        Raises:
            ValueError: If *seconds* is not positive.
        """
        if seconds <= 0:
            raise ValueError(
                f"Timeout for {operation!r} must be positive, got {seconds!r}"
            )
        self._timeouts[operation] = seconds
        logger.debug(
            "timeout_manager.configured",
            operation=operation,
            seconds=seconds,
        )

    def get_timeout(self, operation: str) -> float:
        """Return the effective timeout for *operation*.

        Returns the per-operation override if one has been configured,
        otherwise the manager's default.

        Args:
            operation: The operation name to look up.

        Returns:
            Timeout duration in seconds.
        """
        return self._timeouts.get(operation, self._default)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run(self, operation: str, coro: Awaitable[T]) -> T:
        """Execute *coro* under the timeout configured for *operation*.

        Args:
            operation: The operation name used to look up the timeout.
            coro: The awaitable to run.

        Returns:
            The value produced by *coro*.

        Raises:
            ResilienceTimeoutError: If *coro* does not complete within the
                configured timeout.
        """
        timeout_seconds = self.get_timeout(operation)
        try:
            return await asyncio.wait_for(
                asyncio.ensure_future(coro), timeout=timeout_seconds
            )
        except TimeoutError as exc:
            logger.warning(
                "timeout_manager.timeout",
                operation=operation,
                timeout_seconds=timeout_seconds,
            )
            raise ResilienceTimeoutError(
                f"Operation {operation!r} timed out after {timeout_seconds}s",
                cause=exc,
            ) from exc


__all__ = ["TimeoutManager"]
