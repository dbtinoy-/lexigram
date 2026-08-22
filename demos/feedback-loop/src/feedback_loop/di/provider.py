"""DI wiring for the feedback-loop demo (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

from feedback_loop.loop_service import LoopService


class LoopProvider(Provider):
    """Assembles LoopService from booted collaborators."""

    name = "loop"

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
        except Exception:  # noqa: BLE001 - evaluation module may be absent
            tracker = None

        self._service = LoopService(
            collector=collector,
            tracker=tracker,
        )


__all__ = ["LoopProvider"]
