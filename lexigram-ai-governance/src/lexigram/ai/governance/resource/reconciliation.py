"""Reconciliation worker for INSTANTANEOUS gauge resources.

If a process crashes mid-hold (e.g. an episode-production saga acquires
``concurrent_episodes`` then dies before ``release_resource`` fires), the
gauge drifts upward forever.  This worker periodically queries the
ground-truth count for each registered ``(unit_name, tenant)`` pair and
writes the correct value back to the gauge.

Opt-in per unit by registering a :class:`GaugeReconciliationCallback` with
the worker at boot.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from lexigram.logging import get_logger
from lexigram.tasks import ScheduledWorker

if TYPE_CHECKING:
    from lexigram.ai.governance.resource.tracker import ResourceUnitTracker
    from lexigram.tasks import BackgroundTaskManager

logger = get_logger(__name__)


@runtime_checkable
class GaugeReconciliationCallback(Protocol):
    """Source-of-truth interface for an INSTANTANEOUS gauge.

    Implementations are domain-specific — e.g. for
    ``concurrent_episodes_in_production_per_tenant``, ``count_active`` queries
    the saga store for ``RUNNING`` episode-production sagas owned by *tenant_id*.
    """

    async def list_tenants(self) -> list[str]:
        """Return all tenant IDs to reconcile this cycle."""
        ...

    async def count_active(self, tenant_id: str) -> float:
        """Return the ground-truth held count for *tenant_id*."""
        ...


class GaugeReconciliationWorker(ScheduledWorker):
    """Periodically reconciles INSTANTANEOUS gauges against ground truth.

    Each cycle: for every ``(unit_name, callback)`` registered, list the
    tenants and call ``count_active`` to obtain the correct value; write
    it via :meth:`ResourceUnitTracker.reconcile`.  Per-tenant errors are
    logged and skipped — a single bad callback never poisons the cycle.

    Default cadence is 5 minutes; tunable per-instance.
    """

    interval_seconds: float = 300.0

    def __init__(
        self,
        task_manager: BackgroundTaskManager,
        tracker: ResourceUnitTracker,
        callbacks: dict[str, GaugeReconciliationCallback] | None = None,
        *,
        interval_seconds: float | None = None,
    ) -> None:
        super().__init__(
            task_manager,
            interval_seconds=interval_seconds,
        )
        self._tracker = tracker
        self._callbacks: dict[str, GaugeReconciliationCallback] = dict(callbacks or {})

    def register(self, unit_name: str, callback: GaugeReconciliationCallback) -> None:
        """Register a reconciliation callback for *unit_name*."""
        self._callbacks[unit_name] = callback

    def unregister(self, unit_name: str) -> None:
        """Remove the callback for *unit_name* (no-op if absent)."""
        self._callbacks.pop(unit_name, None)

    @property
    def callbacks(self) -> dict[str, GaugeReconciliationCallback]:
        """Snapshot of currently-registered callbacks."""
        return dict(self._callbacks)

    async def run_cycle(self) -> None:
        for unit_name, callback in list(self._callbacks.items()):
            try:
                tenants = await callback.list_tenants()
            except Exception:
                logger.exception(
                    "gauge_reconciliation.list_tenants_failed",
                    unit_name=unit_name,
                )
                continue
            for tenant_id in tenants:
                try:
                    expected = await callback.count_active(tenant_id)
                    await self._tracker.reconcile(tenant_id, unit_name, expected)
                except Exception:
                    logger.exception(
                        "gauge_reconciliation.failed",
                        unit_name=unit_name,
                        tenant_id=tenant_id,
                    )


__all__ = ["GaugeReconciliationCallback", "GaugeReconciliationWorker"]
