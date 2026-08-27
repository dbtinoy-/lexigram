"""DI wiring for the llm-reproducibility demo.

A Provider tells the DI container *what* exists and *how* to build it.
Two-phase lifecycle: ``register()`` binds, ``boot()`` initializes.

Simplest patterns for new users:

- ``container.singleton(Thing, instance=Thing())`` — already built, hand it over
- ``container.singleton(Thing, factory=lambda: ...)`` — build lazily on first resolve
- ``container.singleton(Thing, factory=self._build_thing)`` — async factory for complex wiring

Don't re-register framework keys (e.g. ``WebConfig``) — the
web module already owns them.
"""

from __future__ import annotations

from lexigram.contracts.core import ProviderPriority
from lexigram.contracts.core.di import ContainerRegistrarProtocol
from lexigram.di.provider import Provider
from llm_reproducibility.config import ExperimentConfig
from llm_reproducibility.services.metrics import JsonMetricsCollector

__all__ = ["ExperimentProvider"]


class ExperimentProvider(Provider):
    """Demo-specific DI registrations — your app replaces this.

    Provider lifecycle: register() → boot() → shutdown().
    register() binds services (no I/O); boot() initializes after freeze.
    """

    name = "experiment"
    priority = ProviderPriority.DOMAIN
    config_key: str | None = "experiment"
    config_model: type | None = ExperimentConfig

    def __init__(self) -> None:
        super().__init__()

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind demo services — no I/O here.

        ``container.singleton(Thing, instance=Thing())`` for already-built objects.
        ``container.singleton(Thing, factory=async_fn)`` for services that need
        other services resolved first (async factories run during resolve).
        """

        # --- Metrics collector: shared across all experiment runs ---
        # JsonMetricsCollector records counters, histograms, and gauges
        # in a deterministic JSON format for digest verification.
        # Register as both the concrete type AND the protocol so
        # framework code can resolve MetricsCollectorProtocol while
        # tests can import JsonMetricsCollector directly.
        container.singleton(JsonMetricsCollector, JsonMetricsCollector)
