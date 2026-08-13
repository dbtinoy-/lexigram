"""Bulkhead pattern implementation."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
import threading
from typing import Any, TypeVar

from lexigram.contracts.observability.metrics import MetricsRecorderProtocol
from lexigram.logging import get_logger
from lexigram.resilience.config import BulkheadConfig
from lexigram.resilience.exceptions import BulkheadRejectedError

T = TypeVar("T")
logger = get_logger(__name__)


class Bulkhead:
    """Bulkhead pattern for limiting concurrent executions."""

    def __init__(
        self,
        config: BulkheadConfig,
        metrics_collector: MetricsRecorderProtocol | None = None,
    ) -> None:
        self.config = config
        self._metrics_collector = metrics_collector
        self.semaphore = asyncio.Semaphore(config.max_concurrent)
        self.queue_semaphore = asyncio.Semaphore(
            config.max_concurrent + config.queue_size,
        )
        self._sync_semaphore = threading.Semaphore(config.max_concurrent)

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a function within the bulkhead."""
        # Try to acquire queue slot
        if self.queue_semaphore.locked():
            if self._metrics_collector:
                self._metrics_collector.increment(
                    "resilience.bulkhead.rejected",
                    tags={"bulkhead": self.config.name or "unnamed"},
                )
            raise BulkheadRejectedError("Bulkhead queue is full")
        await self.queue_semaphore.acquire()

        try:
            # Wait for execution slot with timeout
            try:
                await asyncio.wait_for(
                    self.semaphore.acquire(),
                    timeout=self.config.timeout,
                )
            except TimeoutError:
                if self._metrics_collector:
                    self._metrics_collector.increment(
                        "resilience.bulkhead.timeout",
                        tags={"bulkhead": self.config.name or "unnamed"},
                    )
                raise BulkheadRejectedError(
                    "Timed out waiting for bulkhead slot",
                ) from None

            try:
                if self._metrics_collector:
                    self._metrics_collector.increment(
                        "resilience.bulkhead.calls",
                        tags={"bulkhead": self.config.name or "unnamed"},
                    )
                return await func(*args, **kwargs)
            finally:
                self.semaphore.release()
        finally:
            self.queue_semaphore.release()

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Alias for execute — call a function within the bulkhead."""
        return await self.execute(func, *args, **kwargs)

    def execute_sync(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Call a sync function within the bulkhead using a blocking wait.

        FIX MAJ-2: Uses a dedicated threading.Semaphore for sync safety.
        """
        if not self._sync_semaphore.acquire(timeout=self.config.timeout):
            raise BulkheadRejectedError("Timed out waiting for bulkhead slot (sync)")

        try:
            return func(*args, **kwargs)
        finally:
            self._sync_semaphore.release()


async def bulkhead_context(config: BulkheadConfig) -> Any:
    """Async context manager for bulkhead functionality."""
    # Simplified version for demonstration; real implementation would use a pool
    semaphore = asyncio.Semaphore(config.max_concurrent)
    async with semaphore:
        yield


@dataclass
class AIMDBulkheadMetrics:
    """Metrics for adaptive bulkhead."""

    current_limit: int = 0
    current_usage: int = 0
    total_rejected: int = 0
    total_passed: int = 0
    avg_latency_ms: float = 0.0
    last_adjustment: float = field(
        default_factory=lambda: asyncio.get_event_loop().time(),
    )


@dataclass
class AIMDBulkheadConfig:
    """Configuration for :class:`AIMDBulkhead`.

    Groups all tuning parameters for the AIMD adaptive bulkhead into a single
    configuration object so they can be stored, validated, and passed around
    as a unit rather than as nine flat positional arguments.

    Attributes:
        initial_limit: Starting concurrency limit.
        min_limit: Minimum concurrency limit enforced after decreases.
        max_limit: Maximum concurrency limit allowed after increases.
        increase_amount: Number of slots added per successful low-latency cycle.
        decrease_factor: Multiplier applied when shrinking (default 0.5 = halve).
        increase_threshold_ms: Latency (ms) below which the limit is increased.
        decrease_threshold_ms: Latency (ms) above which the limit is decreased.
        queue_size: Maximum number of calls that may wait for a slot.
        timeout: Seconds to wait before a slot-acquisition attempt times out.
    """

    initial_limit: int = 10
    min_limit: int = 1
    max_limit: int = 100
    increase_amount: int = 1
    decrease_factor: float = 0.5
    increase_threshold_ms: float = 100.0
    decrease_threshold_ms: float = 1000.0
    queue_size: int = 50
    timeout: float = 30.0


class AIMDBulkhead:
    """Adaptive Bulkhead using AIMD (Additive Increase Multiplicative Decrease).

    Implements Netflix-style concurrency limiting that automatically adjusts
    based on latency and error rates:
    - Increases (additive) when latency is low and no errors
    - Decreases (multiplicative) when latency is high or errors occur

    This is more robust than fixed semaphores because it automatically
    shrinks the bulkhead when the downstream service is struggling.
    """

    def __init__(
        self,
        config: AIMDBulkheadConfig,
    ) -> None:
        """Initialize AIMD bulkhead.

        Args:
            config: AIMDBulkheadConfig object (required).
        """
        self._current_limit = config.initial_limit
        self._min_limit = config.min_limit
        self._max_limit = config.max_limit
        self._increase_amount = config.increase_amount
        self._decrease_factor = config.decrease_factor
        self._increase_threshold = config.increase_threshold_ms / 1000.0
        self._decrease_threshold = config.decrease_threshold_ms / 1000.0
        self._queue_size = config.queue_size
        self._timeout = config.timeout

        self._semaphore = asyncio.Semaphore(config.initial_limit)
        self._queue_semaphore = asyncio.Semaphore(
            config.initial_limit + config.queue_size
        )
        self._metrics = AIMDBulkheadMetrics(current_limit=config.initial_limit)
        self._pending_futures: set[asyncio.Future] = set()
        self._lock = asyncio.Lock()
        self._metrics_collector: MetricsRecorderProtocol | None = None
        self._name = "aimd_bulkhead"

    def set_metrics_collector(
        self,
        collector: MetricsRecorderProtocol,
        name: str | None = None,
    ) -> None:
        """Set metrics collector for the bulkhead."""
        self._metrics_collector = collector
        if name:
            self._name = name

    @property
    def metrics(self) -> AIMDBulkheadMetrics:
        """Get current bulkhead metrics."""
        return self._metrics

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    async def _adjust_limit(self, latency: float, success: bool) -> None:
        """Adjust the concurrency limit based on latency and success.

        FIX MAJ-8: Adjust the existing semaphore instead of replacing it to
        avoid stranding waiters (STANDARDS.md 3.4).
        """
        async with self._lock:
            now = asyncio.get_event_loop().time()
            time_since_adjust = now - self._metrics.last_adjustment

            # Only adjust every second to avoid thrashing
            if time_since_adjust < 1.0:
                return

            if success and latency < self._increase_threshold:
                # Good performance - increase limit additively
                new_limit = min(
                    self._current_limit + self._increase_amount,
                    self._max_limit,
                )
            elif latency > self._decrease_threshold or not success:
                # High latency or failure - decrease limit multiplicatively
                new_limit = max(
                    int(self._current_limit * self._decrease_factor),
                    self._min_limit,
                )
            else:
                return

            if new_limit != self._current_limit:
                diff = new_limit - self._current_limit
                if diff > 0:
                    for _ in range(diff):
                        self._semaphore.release()
                        self._queue_semaphore.release()
                else:
                    for _ in range(-diff):
                        fut_s = asyncio.ensure_future(self._semaphore.acquire())
                        self._pending_futures.add(fut_s)
                        fut_s.add_done_callback(self._pending_futures.discard)
                        fut_q = asyncio.ensure_future(self._queue_semaphore.acquire())
                        self._pending_futures.add(fut_q)
                        fut_q.add_done_callback(self._pending_futures.discard)

                self._current_limit = new_limit
                self._metrics.last_adjustment = now
                self._metrics.current_limit = new_limit

                if self._metrics_collector:
                    self._metrics_collector.gauge(
                        "resilience.bulkhead.limit",
                        value=float(new_limit),
                        tags={"bulkhead": self._name},
                    )

                logger.debug("AIMD bulkhead adjusted limit to %d", new_limit)

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a function within the adaptive bulkhead."""
        start_time = asyncio.get_event_loop().time()

        # Try to acquire queue slot
        if self._queue_semaphore.locked():
            self._metrics.total_rejected += 1
            if self._metrics_collector:
                self._metrics_collector.increment(
                    "resilience.bulkhead.rejected",
                    tags={"bulkhead": self._name},
                )
            raise BulkheadRejectedError("AIMD Bulkhead queue is full")

        await self._queue_semaphore.acquire()

        try:
            # Wait for execution slot with timeout
            try:
                await asyncio.wait_for(
                    self._semaphore.acquire(),
                    timeout=self._timeout,
                )
            except TimeoutError:
                self._metrics.total_rejected += 1
                if self._metrics_collector:
                    self._metrics_collector.increment(
                        "resilience.bulkhead.timeout",
                        tags={"bulkhead": self._name},
                    )
                raise BulkheadRejectedError(
                    "Timed out waiting for AIMD bulkhead slot",
                ) from None

            try:
                result = await func(*args, **kwargs)
                latency = asyncio.get_event_loop().time() - start_time
                self._metrics.total_passed += 1

                if self._metrics_collector:
                    self._metrics_collector.increment(
                        "resilience.bulkhead.calls",
                        tags={"bulkhead": self._name, "status": "success"},
                    )
                    self._metrics_collector.gauge(
                        "resilience.bulkhead.latency_ms",
                        value=latency * 1000,
                        tags={"bulkhead": self._name},
                    )
                self._metrics.avg_latency_ms = (
                    self._metrics.avg_latency_ms * 0.95 + latency * 1000 * 0.05
                )

                # Adjust limit based on performance
                await self._adjust_limit(latency, success=True)

                return result
            except BaseException:
                latency = asyncio.get_event_loop().time() - start_time
                self._metrics.total_rejected += 1

                if self._metrics_collector:
                    self._metrics_collector.increment(
                        "resilience.bulkhead.calls",
                        tags={"bulkhead": self._name, "status": "failure"},
                    )

                # Adjust limit based on failure
                await self._adjust_limit(latency, success=False)

                raise
            finally:
                self._semaphore.release()
        finally:
            self._queue_semaphore.release()


__all__ = [
    "AIMDBulkhead",
    "AIMDBulkheadMetrics",
    "Bulkhead",
    "BulkheadConfig",
    "BulkheadRejectedError",
    "bulkhead_context",
]
