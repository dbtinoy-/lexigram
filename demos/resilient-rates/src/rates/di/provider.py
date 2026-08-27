"""Provider wiring for the resilient rates demo.

Convention followed: **Provider pattern** — ``RatesProvider`` is the
canonical shape (mirrors ``lexigram-auth`` + the boot-phase ``bind()``
contract in ``lexigram.contracts.core.di``):

- ``config_key``/``config_model`` declare the ``demo:`` section; the
  orchestrator injects the matching typed section of ``LexigramConfig``
  into ``provider.config`` right before ``register()`` runs.
- ``register()`` only *declares* bindings.  Zero-arg factories cover
  purely config-derived services; dependency-full services are declared
  as class bindings and instantiated in :meth:`boot`.
- ``boot()`` resolves cross-module dependencies (cache backend,
  resilience pipeline) after every provider has registered and rebinds
  the concrete instances via ``container.bind()``.
- Controllers are constructed by the router from the container; ``boot``
  binds their prebuilt instances so per-request resolution reuses them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.cache import CacheConfig
from lexigram.cache.service.stampede import StampedeProtectedCache
from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.contracts.infra.resilience import ResiliencePipelineFactoryProtocol
from lexigram.di.provider import Provider
from rates.config import RatesConfig
from rates.controllers import RatesApiController
from rates.repository import FaultController, Scenario, SimulatedRatesProvider
from rates.services import RatesService

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

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; concrete wiring happens in :meth:`boot`."""
        cfg = self.config or RatesConfig()

        container.singleton(RatesConfig, instance=cfg)
        container.singleton(StampedeProtectedCache, StampedeProtectedCache)
        container.singleton(
            FaultController,
            factory=lambda: FaultController(initial=Scenario(cfg.upstream_scenario)),
        )
        # Class bindings so the keys exist; boot() replaces them with
        # fully-wired instances via container.bind().
        container.singleton(SimulatedRatesProvider, SimulatedRatesProvider)
        container.singleton(RatesService, RatesService)
        container.singleton(RatesApiController, RatesApiController)

    def _default_ttl(self, cache_config: CacheConfig) -> int | None:
        """Read ``default_ttl`` off the default backend, if configured."""
        for backend in cache_config.backends:
            if backend.default and backend.default_ttl is not None:
                return backend.default_ttl
        return None

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve cross-module dependencies and bind concrete instances."""
        faults = await container.resolve(FaultController)
        backend = await container.resolve(CacheBackendProtocol)
        cache_config = await container.resolve(CacheConfig)

        container.bind(
            SimulatedRatesProvider,
            SimulatedRatesProvider(faults=faults),
        )

        protection = StampedeProtectedCache(cache=backend)
        container.bind(StampedeProtectedCache, protection)

        service = RatesService(
            cache=backend,
            protection=protection,
            pipeline_factory=await container.resolve(ResiliencePipelineFactoryProtocol),
            provider=await container.resolve(SimulatedRatesProvider),
            faults=faults,
            cache_ttl=self._default_ttl(cache_config),
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
