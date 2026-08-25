"""Resource-unit consumption gateway for governance.

Wraps the optional
:class:`~lexigram.ai.governance.resource.tracker.ResourceUnitTracker` so
the manager exposes uniform consume/release/usage semantics whether or
not resource units are configured.  Without a tracker, consumption is
denied with a zero-limit :class:`ResourceExhaustedError` and usage reads
return an empty snapshot — never an invented measurement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai.governance.resource_unit import (
    ResourceExhaustedError,
    ResourceUsageSnapshot,
)
from lexigram.result import Err, Result

if TYPE_CHECKING:
    from lexigram.ai.governance.config import GovernanceConfig
    from lexigram.ai.governance.persistence import GovernancePersistence
    from lexigram.ai.governance.resource.registry import ResourceUnitRegistry
    from lexigram.ai.governance.resource.tracker import ResourceUnitTracker

__all__ = ["ResourceUnitCoordinator"]


class ResourceUnitCoordinator:
    """Owns the optional resource-unit registry/tracker pair.

    Builds the registry and tracker from *config* when resource units are
    configured; otherwise holds ``None`` for both so consumers can detect
    the disabled state.

    Args:
        config: Governance configuration (read for ``resource_units``).
        persistence: Persistence backend shared with the tracker.
    """

    def __init__(
        self,
        config: GovernanceConfig,
        persistence: GovernancePersistence,
    ) -> None:
        if config.resource_units:
            from lexigram.ai.governance.resource.registry import (
                ResourceUnitRegistry,
            )
            from lexigram.ai.governance.resource.tracker import (
                ResourceUnitTracker,
            )

            self._registry: ResourceUnitRegistry | None = (
                ResourceUnitRegistry.from_list(config.resource_units)
            )
            self._tracker: ResourceUnitTracker | None = ResourceUnitTracker(
                registry=self._registry,
                persistence=persistence,
            )
        else:
            self._registry = None
            self._tracker = None

    @property
    def tracker(self) -> ResourceUnitTracker | None:
        """The tracker instance, or ``None`` when no units are configured.

        Exposed for DI registration so the same tracker is shared across
        the application.
        """
        return self._tracker

    async def consume(
        self,
        tenant_id: str,
        unit_name: str,
        amount: float,
        actor_id: str | None = None,
    ) -> Result:
        """Consume *amount* of a resource unit for *tenant_id*.

        Delegates to the tracker when configured; returns ``Err`` with a
        zero-limit :class:`ResourceExhaustedError` otherwise.
        """
        if self._tracker is None:
            return Err(self._no_tracker_error(tenant_id, unit_name, amount))
        return await self._tracker.consume(tenant_id, unit_name, amount, actor_id)

    async def release(
        self,
        tenant_id: str,
        unit_name: str,
        amount: float,
    ) -> None:
        """Release *amount* of a held resource (INSTANTANEOUS units only)."""
        if self._tracker is None:
            return
        await self._tracker.release(tenant_id, unit_name, amount)

    async def usage(self, tenant_id: str, unit_name: str):
        """Return current usage snapshot for *tenant_id* + *unit_name*."""
        if self._tracker is None:
            return ResourceUsageSnapshot(
                tenant_id=tenant_id,
                unit_name=unit_name,
                current=0.0,
                limit=0.0,
            )
        return await self._tracker.usage(tenant_id, unit_name)

    def _no_tracker_error(
        self, tenant_id: str, unit_name: str, amount: float
    ) -> ResourceExhaustedError:
        return ResourceExhaustedError(
            tenant_id=tenant_id,
            unit_name=unit_name,
            limit=0,
            current=0,
        )
