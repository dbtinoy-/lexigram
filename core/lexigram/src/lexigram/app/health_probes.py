"""Health probe surface for :class:`~lexigram.app.base.Application`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.health import (
    AggregateHealthResult,
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)

if TYPE_CHECKING:
    from lexigram.app.base import AppState


class HealthProbeMixin:
    """Aggregate health/liveness/readiness probes over all providers.

    State attributes (``_state``, ``name``, ``_orchestrator``) are owned by
    :class:`~lexigram.app.base.Application`.
    """

    if TYPE_CHECKING:
        _state: AppState
        name: str
        _orchestrator: Any

    async def health_check(self, timeout: float = 5.0) -> AggregateHealthResult:
        """Aggregate health check from all providers.

        Returns an :class:`~lexigram.contracts.core.health.AggregateHealthResult`
        whose ``status`` follows worst-case aggregation across all registered
        provider health checks.
        """
        from lexigram.app.base import AppState  # local: avoid circular import

        if self._state != AppState.RUNNING:
            return AggregateHealthResult(
                components=[
                    HealthCheckResult(
                        component=self.name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Application is {self._state.value}",
                    )
                ]
            )

        raw: dict[str, Any] = await self._orchestrator.health_check(timeout)
        return AggregateHealthResult(components=list(raw.values()))

    def _probe_unavailable_result(
        self,
        category: HealthCheckCategory,
    ) -> AggregateHealthResult:
        """Build a probe result when the application is not running."""
        return AggregateHealthResult(
            components=[
                HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Application is {self._state.value}",
                    category=category,
                ),
            ],
        )

    async def liveness(self, timeout: float = 5.0) -> AggregateHealthResult:
        """Run liveness checks for the application."""
        from lexigram.app.base import AppState  # local: avoid circular import

        if self._state != AppState.RUNNING:
            return self._probe_unavailable_result(HealthCheckCategory.LIVENESS)
        return await self._orchestrator.run_liveness(timeout)

    async def readiness(self, timeout: float = 5.0) -> AggregateHealthResult:
        """Run readiness checks for the application."""
        from lexigram.app.base import AppState  # local: avoid circular import

        if self._state != AppState.RUNNING:
            return self._probe_unavailable_result(HealthCheckCategory.READINESS)
        return await self._orchestrator.run_readiness(timeout)


__all__ = ["HealthProbeMixin"]
