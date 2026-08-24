"""Provider binding the experiment runtime dependencies."""

from __future__ import annotations

from pathlib import Path

from lexigram.contracts.core import ProviderPriority
from lexigram.contracts.core.di import ContainerRegistrarProtocol
from lexigram.di.provider import Provider
from llm_reproducibility.metrics import JsonMetricsCollector


class ExperimentProvider(Provider):
    """Registers the shared JSON metrics sink for experiment runs."""

    name = "experiment"
    priority = ProviderPriority.DOMAIN

    def __init__(self, runs_dir: Path | None = None) -> None:
        self._runs_dir = runs_dir

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(JsonMetricsCollector, JsonMetricsCollector)


__all__ = ["ExperimentProvider"]
