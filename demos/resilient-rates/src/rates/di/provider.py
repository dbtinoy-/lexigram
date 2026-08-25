"""Provider wiring for the resilient rates demo.

Canonical shape (mirrors ``lexigram-auth`` + the boot-phase ``bind()``
contract in ``lexigram.contracts.core.di``):

- ``config_key``/``config_model`` declare the ``demo:`` section so the
  framework injects a bound :class:`RatesConfig` when the application's
  ``LexigramConfig`` carries it; an explicit ``config=`` from
  ``RatesModule.configure`` (bound against the demo's own
  ``application.yaml``) takes precedence.
- ``register()`` only *declares* bindings. Zero-arg factories cover purely
  config-derived services; dependency-full services are declared as
  class bindings and instantiated in :meth:`boot`.
- ``boot()`` resolves cross-module dependencies (cache backend, resilience
  pipeline) after every provider has registered and rebinds the concrete
  instances via ``container.bind()``.
- Controllers are constructed by the router from the container; ``boot``
  binds their prebuilt instances so per-request resolution reuses them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
from lexigram.contracts.infra.resilience.protocols import (
    ResiliencePipelineFactoryProtocol,
)
from lexigram.di.provider import Provider
from rates.config import RatesConfig
from rates.controllers.api import RatesApiController
from rates.repository.simulated_upstream import (
    FaultController,
    Scenario,
    SimulatedRatesProvider,
)
from rates.services.rates_service import RatesService

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

__all__ = ["RatesProvider"]


class RatesProvider(Provider):
    """Bind the rate desk services as container-managed singletons."""

    name = "rates"

    config_key: str | None = "demo"
    config_model: type | None = RatesConfig

    def __init__(self, config: RatesConfig | None = None) -> None:
        super().__init__()
        self._config = config or RatesConfig()

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; concrete wiring happens in :meth:`boot`."""
        cfg = self.config or RatesConfig()

        container.singleton(RatesConfig, instance=cfg)
        container.singleton(
            FaultController,
            factory=lambda: FaultController(initial=Scenario(cfg.upstream_scenario)),
        )
        # Class bindings so the keys exist; boot() replaces them with
        # fully-wired instances via container.bind().
        container.singleton(SimulatedRatesProvider, SimulatedRatesProvider)
        container.singleton(RatesService, RatesService)
        container.singleton(RatesApiController, RatesApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve cross-module dependencies and bind concrete instances."""
        faults = await container.resolve(FaultController)

        container.bind(
            SimulatedRatesProvider,
            SimulatedRatesProvider(faults=faults),
        )

        service = RatesService(
            cache=await container.resolve(CacheBackendProtocol),
            pipeline_factory=await container.resolve(ResiliencePipelineFactoryProtocol),
            provider=await container.resolve(SimulatedRatesProvider),
            faults=faults,
            cache_ttl_seconds=(self.config or RatesConfig()).cache_ttl_seconds,
        )
        container.bind(RatesService, service)

        container.bind(
            RatesApiController,
            RatesApiController(service=service, faults=faults),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the rate desk."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
