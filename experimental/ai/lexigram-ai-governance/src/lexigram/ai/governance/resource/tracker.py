"""Resource unit tracker — consume/release/usage for non-LLM resources."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from lexigram.contracts.ai.governance.resource_unit import (
    ResourceExhaustedError,
    ResourceUnit,
    ResourceUsageSnapshot,
    ResourceWindowKind,
)
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.ai.governance.persistence import GovernancePersistence
    from lexigram.ai.governance.resource.registry import (
        ResourceUnitRegistry,
    )

logger = get_logger(__name__)

_DEFAULT_TTL = 3600


class ResourceUnitTracker:
    """Tracks per-tenant resource consumption via the persistence layer.

    Routes ``consume`` / ``release`` / ``usage`` calls to the right
    persistence method based on the unit's ``window_kind``:

    * ``SLIDING`` → ``incr_requests`` (existing sliding-window counter)
    * ``CALENDAR`` → ``incr_calendar`` / ``get_calendar``
    * ``INSTANTANEOUS`` → ``incr_gauge`` / ``decr_gauge`` / ``read_gauge``

    Args:
        registry: Registry of known :class:`ResourceUnit` definitions.
        persistence: Backend that implements
            :class:`~lexigram.ai.governance.persistence.GovernancePersistence`.
        get_quota: Callable ``(tenant_id, unit_name) → limit``.  Return
            ``0.0`` to deny all usage.
    """

    def __init__(
        self,
        registry: ResourceUnitRegistry,
        persistence: GovernancePersistence,
        get_quota: Callable[[str, str], float] | None = None,
    ) -> None:
        self._registry = registry
        self._persistence = persistence
        self._get_quota = get_quota or (lambda _tid, _un: 0.0)

    async def consume(
        self,
        tenant_id: str,
        unit_name: str,
        amount: float,
        actor_id: str | None = None,
    ) -> Result[ResourceUsageSnapshot, ResourceExhaustedError]:
        """Consume *amount* of a resource for *tenant_id*.

        Returns:
            ``Ok(snapshot)`` on success, ``Err(ResourceExhaustedError)`` if the
            quota would be exceeded.
        """
        unit = self._registry.get_unit(unit_name)
        if unit is None:
            return Err(
                ResourceExhaustedError(
                    tenant_id=tenant_id,
                    unit_name=unit_name,
                    limit=0,
                    current=0,
                    actor_id=actor_id,
                )
            )

        limit = self._get_quota(tenant_id, unit_name)
        if limit <= 0:
            return Err(
                ResourceExhaustedError(
                    tenant_id=tenant_id,
                    unit_name=unit_name,
                    limit=0,
                    current=0,
                    actor_id=actor_id,
                )
            )

        current = await self._record_usage(unit, tenant_id, amount)
        # INSTANTANEOUS reads pre-increment value so use >=; others use >
        exhausted = (
            current >= limit
            if unit.window_kind == ResourceWindowKind.INSTANTANEOUS
            else current > limit
        )
        if exhausted:
            logger.warning(
                "resource_exhausted",
                tenant_id=tenant_id,
                unit_name=unit_name,
                current=current,
                limit=limit,
            )
            return Err(
                ResourceExhaustedError(
                    tenant_id=tenant_id,
                    unit_name=unit_name,
                    limit=limit,
                    current=current,
                    actor_id=actor_id,
                )
            )

        # Apply actual increment for INSTANTANEOUS after limit check passes
        final_current = current
        if unit.window_kind == ResourceWindowKind.INSTANTANEOUS and amount > 0:
            final_current = await self._persistence.incr_gauge(
                self._gauge_key(tenant_id, unit_name),
                amount,
                _DEFAULT_TTL,
            )

        return Ok(
            ResourceUsageSnapshot(
                tenant_id=tenant_id,
                unit_name=unit_name,
                current=float(final_current),
                limit=limit,
            )
        )

    async def release(self, tenant_id: str, unit_name: str, amount: float) -> None:
        """Release *amount* of a held resource (INSTANTANEOUS units only).

        For SLIDING and CALENDAR windows this is a no-op — windows decay
        naturally.
        """
        unit = self._registry.get_unit(unit_name)
        if unit is None:
            return
        if unit.window_kind != ResourceWindowKind.INSTANTANEOUS:
            return
        await self._persistence.decr_gauge(
            self._gauge_key(tenant_id, unit_name),
            amount,
            _DEFAULT_TTL,
        )

    async def reconcile(
        self,
        tenant_id: str,
        unit_name: str,
        expected_amount: float,
    ) -> None:
        """Reset the gauge for an INSTANTANEOUS unit to *expected_amount*.

        Used by :class:`GaugeReconciliationWorker` to repair drift caused by
        crashed processes that consumed without releasing.  No-op for
        non-INSTANTANEOUS units.
        """
        unit = self._registry.get_unit(unit_name)
        if unit is None or unit.window_kind != ResourceWindowKind.INSTANTANEOUS:
            return
        await self._persistence.write_gauge(
            self._gauge_key(tenant_id, unit_name),
            max(expected_amount, 0.0),
            _DEFAULT_TTL,
        )

    async def usage(self, tenant_id: str, unit_name: str) -> ResourceUsageSnapshot:
        """Return current usage snapshot for *tenant_id* + *unit_name*."""
        unit = self._registry.get_unit(unit_name)
        limit = self._get_quota(tenant_id, unit_name)
        if unit is None:
            return ResourceUsageSnapshot(
                tenant_id=tenant_id,
                unit_name=unit_name,
                current=0.0,
                limit=limit,
            )
        current = await self._read_usage(unit, tenant_id)
        return ResourceUsageSnapshot(
            tenant_id=tenant_id,
            unit_name=unit_name,
            current=float(current),
            limit=limit,
        )

    # -- private helpers -----------------------------------------------------

    async def _record_usage(
        self, unit: ResourceUnit, tenant_id: str, amount: float
    ) -> float:
        kind = unit.window_kind
        if kind == ResourceWindowKind.SLIDING:
            window_sec = unit.window.total_seconds() if unit.window else 60
            return await self._persistence.incr_requests(
                self._sliding_key(tenant_id, unit.name), window_sec
            )
        if kind == ResourceWindowKind.CALENDAR:
            ttl = int(unit.window.total_seconds()) if unit.window else 86400
            period = self._calendar_period(unit)
            return await self._persistence.incr_calendar(
                self._cal_key(tenant_id, unit.name),
                period,
                amount,
                ttl,
            )
        if kind == ResourceWindowKind.INSTANTANEOUS:
            return float(
                await self._persistence.read_gauge(
                    self._gauge_key(tenant_id, unit.name)
                )
            )
        return 0.0

    async def _read_usage(self, unit: ResourceUnit, tenant_id: str) -> float:
        kind = unit.window_kind
        if kind == ResourceWindowKind.SLIDING:
            window_sec = unit.window.total_seconds() if unit.window else 60
            count = await self._persistence.incr_requests(
                self._sliding_key(tenant_id, unit.name), window_sec
            )
            return float(count - 1)
        if kind == ResourceWindowKind.CALENDAR:
            period = self._calendar_period(unit)
            return await self._persistence.get_calendar(
                self._cal_key(tenant_id, unit.name), period
            )
        if kind == ResourceWindowKind.INSTANTANEOUS:
            return float(
                await self._persistence.read_gauge(
                    self._gauge_key(tenant_id, unit.name)
                )
            )
        return 0.0

    @staticmethod
    def _sliding_key(tenant_id: str, unit_name: str) -> str:
        return f"sliding:{tenant_id}:{unit_name}"

    @staticmethod
    def _gauge_key(tenant_id: str, unit_name: str) -> str:
        return f"gauge:{tenant_id}:{unit_name}"

    @staticmethod
    def _cal_key(tenant_id: str, unit_name: str) -> str:
        return f"cal:{tenant_id}:{unit_name}"

    @staticmethod
    def _calendar_period(unit: ResourceUnit) -> str:
        from datetime import UTC

        from lexigram.primitives import clock

        now = clock.now()
        if unit.window and unit.window.total_seconds() >= 86400 * 27:
            return now.astimezone(UTC).strftime("%Y-%m")
        return now.astimezone(UTC).strftime("%Y-%m-%d")


__all__ = ["ResourceUnitTracker"]
