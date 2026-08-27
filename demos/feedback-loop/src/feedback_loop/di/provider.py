"""DI wiring for the feedback-loop demo (internal).

A Provider tells the DI container *what* exists and *how* to build it.
Two-phase lifecycle: ``register()`` binds, ``boot()`` initialises.

Simplest patterns for new users:

- ``container.singleton(Thing, instance=Thing())`` — already built, hand it over
- ``container.singleton(Thing, factory=lambda: ...)`` — build lazily on first resolve
- ``container.singleton(Thing, factory=self._build_thing)`` — async factory for complex wiring

Convention: providers contain no business logic — only registration,
boot wiring, and shutdown cleanup.  ``LoopProvider`` assembles
``LoopService`` from its collaborators (``FeedbackCollector``,
``ExperimentTrackerProtocol``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from feedback_loop.services import LoopService
from lexigram.contracts.core.health import HealthCheckResult
from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class LoopProvider(Provider):
    """Assembles LoopService from booted collaborators."""

    name = "loop"

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report component readiness with live counters."""
        return HealthCheckResult(
            component=self.name,
            details={
                "tracker_bound": self._service is not None
                and self._service._tracker is not None
            },
        )

    def __init__(self) -> None:
        super().__init__()
        self._service: LoopService | None = None

    def _get_service(self) -> LoopService:
        if self._service is None:
            raise RuntimeError("LoopProvider has not been booted yet")
        return self._service

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind the lazy factory; collaborators resolve in boot()."""
        container.singleton(LoopService, factory=self._get_service)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve collector + tracker; harness/evaluator built locally."""
        from lexigram.ai.feedback.services.collector import FeedbackCollector
        from lexigram.contracts.ai.experiment import ExperimentTrackerProtocol

        collector = await container.resolve(FeedbackCollector)
        try:
            tracker = await container.resolve(ExperimentTrackerProtocol)
        except LookupError:
            tracker = None

        self._service = LoopService(
            collector=collector,
            tracker=tracker,
        )


__all__ = ["LoopProvider"]
