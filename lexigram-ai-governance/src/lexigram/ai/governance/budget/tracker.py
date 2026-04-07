"""Budget tracker — TPM (tokens-per-minute) + sliding-window cost enforcement.

Extends the existing RPM-based governance with:
* TPM enforcement using a sliding-window counter.
* Per-model and per-tenant cost tracking.
* Budget alert events at configurable thresholds (80%, 90%, 100%) emitted
  via ``EventBusProtocol``.
* ``Result``-based API — policy violations return ``Err``, infrastructure
  errors raise.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
import time
from typing import TYPE_CHECKING, Any

from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.events import EventBusProtocol

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

_ALERT_THRESHOLDS = (0.80, 0.90, 1.00)


@dataclass
class BudgetApproval:
    """Returned when a budget check passes.

    Attributes:
        remaining_tokens: Remaining TPM capacity for this window.
        remaining_cost: Remaining cost budget for the current period.
    """

    remaining_tokens: int | None
    remaining_cost: float | None


@dataclass
class BudgetExceeded:
    """Domain error returned when a request would exceed a budget limit.

    Attributes:
        limit_type: ``"tpm"`` or ``"cost"``.
        current: Current value in the windows.
        limit: Configured limit.
        model: Model identifier.
        tenant_id: Tenant identifier (if applicable).
    """

    limit_type: str
    current: float
    limit: float
    model: str
    tenant_id: str | None = None


@dataclass
class BudgetAlertEvent:
    """Domain event emitted when a budget threshold is crossed.

    Attributes:
        threshold: The fraction threshold that was crossed (0.8, 0.9, 1.0).
        limit_type: ``"tpm"`` or ``"cost"``.
        current: Current value.
        limit: Configured limit.
        model: Model identifier.
        tenant_id: Tenant identifier.
    """

    threshold: float
    limit_type: str
    current: float
    limit: float
    model: str
    tenant_id: str | None = None


# ---------------------------------------------------------------------------
# Sliding-window counter
# ---------------------------------------------------------------------------


class _SlidingWindowCounter:
    """Thread-safe sliding window counter for rate / budget enforcement.

    Uses a deque of ``(timestamp, value)`` tuples.  On each access,
    entries older than *window_seconds* are dropped.
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._window = window_seconds
        self._entries: deque[tuple[float, float]] = deque()
        self._lock = asyncio.Lock()

    async def add(self, value: float) -> float:
        """Record *value* and return the updated window total.

        Args:
            value: Value to add (token count, cost in USD, etc.).

        Returns:
            Sum of all values in the current window after adding *value*.
        """
        now = time.monotonic()
        async with self._lock:
            self._entries.append((now, value))
            self._prune(now)
            return sum(v for _, v in self._entries)

    async def total(self) -> float:
        """Return the current window total without adding a new entry."""
        now = time.monotonic()
        async with self._lock:
            self._prune(now)
            return sum(v for _, v in self._entries)

    def _prune(self, now: float) -> None:
        cutoff = now - self._window
        while self._entries and self._entries[0][0] < cutoff:
            self._entries.popleft()


# ---------------------------------------------------------------------------
# BudgetTracker
# ---------------------------------------------------------------------------


class BudgetTracker:
    """Track and enforce TPM (tokens-per-minute) + cost budgets.

    Maintains per-model and per-tenant sliding windows.  When a request
    would push a window over its limit, returns ``Err(BudgetExceeded)``.
    Emits :class:`BudgetAlertEvent` domain events at configurable thresholds
    (80%, 90%, 100%) via an optional ``EventBusProtocol``.

    Example::

        tracker = BudgetTracker(
            tpm_limit=100_000,
            cost_limit_hourly=10.0,
        )
        result = await tracker.check_budget("gpt-4", estimated_tokens=500)
        if result.is_err():
            raise PermissionError(str(result.unwrap_err()))

        # After the LLM call succeeds:
        await tracker.record_usage("gpt-4", tokens_used=480, cost=0.024)
    """

    def __init__(
        self,
        *,
        tpm_limit: int | None = None,
        cost_limit_hourly: float | None = None,
        window_seconds: float = 60.0,
        event_bus: EventBusProtocol | None = None,
    ) -> None:
        """Initialize the budget tracker.

        Args:
            tpm_limit: Maximum tokens per minute (across all models).  When
                ``None``, TPM is not enforced.
            cost_limit_hourly: Maximum USD cost per hour.  When ``None``,
                cost is tracked but not enforced.
            window_seconds: Sliding window size in seconds (default 60 s for
                TPM; cost window is 3600 s internally).
            event_bus: Optional event bus for publishing
                :class:`BudgetAlertEvent` domain events.
        """
        self._tpm_limit = tpm_limit
        self._cost_limit = cost_limit_hourly
        self._event_bus = event_bus

        # Counters keyed by ``"<model>:<tenant_id>"`` (or ``"<model>:global"``)
        self._token_counters: dict[str, _SlidingWindowCounter] = {}
        self._cost_counters: dict[str, _SlidingWindowCounter] = {}

        self._tpm_window = window_seconds
        self._cost_window = 3600.0  # 1-hour sliding window for cost

        self._alerted_thresholds: dict[str, set[float]] = {}

    def _counter_key(self, model: str, tenant_id: str | None) -> str:
        return f"{model}:{tenant_id or 'global'}"

    def _get_token_counter(self, key: str) -> _SlidingWindowCounter:
        if key not in self._token_counters:
            self._token_counters[key] = _SlidingWindowCounter(self._tpm_window)
        return self._token_counters[key]

    def _get_cost_counter(self, key: str) -> _SlidingWindowCounter:
        if key not in self._cost_counters:
            self._cost_counters[key] = _SlidingWindowCounter(self._cost_window)
        return self._cost_counters[key]

    async def check_budget(
        self,
        model: str,
        estimated_tokens: int,
        *,
        estimated_cost: float = 0.0,
        tenant_id: str | None = None,
    ) -> Result[BudgetApproval, BudgetExceeded]:
        """Check whether a request fits within budget limits.

        This method is read-only — it does NOT record usage.  Call
        :meth:`record_usage` after a successful LLM call.

        Args:
            model: Model identifier.
            estimated_tokens: Estimated token count for the request.
            estimated_cost: Estimated USD cost for the request.
            tenant_id: Optional tenant identifier for per-tenant limits.

        Returns:
            ``Ok(BudgetApproval)`` if within budget,
            ``Err(BudgetExceeded)`` if the limit would be exceeded.
        """
        key = self._counter_key(model, tenant_id)

        if self._tpm_limit is not None:
            current_tpm = await self._get_token_counter(key).total()
            if current_tpm + estimated_tokens > self._tpm_limit:
                logger.warning(
                    "budget_tracker_tpm_exceeded",
                    model=model,
                    current_tpm=current_tpm,
                    tpm_limit=self._tpm_limit,
                    tenant_id=tenant_id,
                )
                return Err(
                    BudgetExceeded(
                        limit_type="tpm",
                        current=current_tpm,
                        limit=float(self._tpm_limit),
                        model=model,
                        tenant_id=tenant_id,
                    )
                )

        if self._cost_limit is not None and estimated_cost > 0:
            current_cost = await self._get_cost_counter(key).total()
            if current_cost + estimated_cost > self._cost_limit:
                logger.warning(
                    "budget_tracker_cost_exceeded",
                    model=model,
                    current_cost=current_cost,
                    cost_limit=self._cost_limit,
                    tenant_id=tenant_id,
                )
                return Err(
                    BudgetExceeded(
                        limit_type="cost",
                        current=current_cost,
                        limit=self._cost_limit,
                        model=model,
                        tenant_id=tenant_id,
                    )
                )

        remaining_tokens = (
            (self._tpm_limit - int(await self._get_token_counter(key).total()))
            if self._tpm_limit is not None
            else None
        )
        remaining_cost = (
            (self._cost_limit - await self._get_cost_counter(key).total())
            if self._cost_limit is not None
            else None
        )
        return Ok(
            BudgetApproval(
                remaining_tokens=remaining_tokens, remaining_cost=remaining_cost
            )
        )

    async def record_usage(
        self,
        model: str,
        tokens_used: int,
        cost: float,
        *,
        tenant_id: str | None = None,
    ) -> None:
        """Record actual token usage and cost after a completed LLM call.

        Args:
            model: Model identifier.
            tokens_used: Actual tokens consumed.
            cost: Actual cost in USD.
            tenant_id: Optional tenant identifier.
        """
        key = self._counter_key(model, tenant_id)
        new_tpm = await self._get_token_counter(key).add(float(tokens_used))
        new_cost = await self._get_cost_counter(key).add(cost)

        # Emit alert events at threshold crossings
        await self._check_alerts(
            key, model, tenant_id, "tpm", new_tpm, float(self._tpm_limit or 0)
        )
        await self._check_alerts(
            key, model, tenant_id, "cost", new_cost, self._cost_limit or 0.0
        )

    async def _check_alerts(
        self,
        key: str,
        model: str,
        tenant_id: str | None,
        limit_type: str,
        current: float,
        limit: float,
    ) -> None:
        """Emit alert events when thresholds are crossed."""
        if limit <= 0 or self._event_bus is None:
            return

        alerted = self._alerted_thresholds.setdefault(f"{key}:{limit_type}", set())
        fraction = current / limit

        for threshold in _ALERT_THRESHOLDS:
            if fraction >= threshold and threshold not in alerted:
                alerted.add(threshold)
                event = BudgetAlertEvent(
                    threshold=threshold,
                    limit_type=limit_type,
                    current=current,
                    limit=limit,
                    model=model,
                    tenant_id=tenant_id,
                )
                result = await self._event_bus.publish(event)
                if result.is_err():
                    logger.warning(
                        "budget_alert_publish_failed",
                        threshold=threshold,
                        limit_type=limit_type,
                        error=str(result.unwrap_err()),
                    )

    async def get_usage(
        self, model: str, *, tenant_id: str | None = None
    ) -> dict[str, Any]:
        """Return current usage totals for a model/tenant combination.

        Args:
            model: Model identifier.
            tenant_id: Optional tenant identifier.

        Returns:
            Dict with ``tokens_per_minute`` and ``cost_per_hour`` keys.
        """
        key = self._counter_key(model, tenant_id)
        return {
            "tokens_per_minute": await self._get_token_counter(key).total(),
            "cost_per_hour": await self._get_cost_counter(key).total(),
            "tpm_limit": self._tpm_limit,
            "cost_limit_hourly": self._cost_limit,
        }

    def reset_alerts(self, model: str, *, tenant_id: str | None = None) -> None:
        """Reset threshold-alert state for a model/tenant (e.g. on period rollover).

        Args:
            model: Model identifier.
            tenant_id: Optional tenant identifier.
        """
        key = self._counter_key(model, tenant_id)
        for limit_type in ("tpm", "cost"):
            self._alerted_thresholds.pop(f"{key}:{limit_type}", None)


__all__ = [
    "BudgetAlertEvent",
    "BudgetApproval",
    "BudgetExceeded",
    "BudgetTracker",
]
