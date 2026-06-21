from __future__ import annotations

from typing import Any

from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.infra.resilience import (
    CircuitBreakerConfig,
    CircuitBreakerRegistryProtocol,
    ResiliencePipelineFactoryProtocol,
    ResiliencePipelineProtocol,
    RetryConfig,
    TimeoutConfig,
)
from lexigram.di.provider import Provider, ProviderPriority
from lexigram.logging import get_logger
from lexigram.resilience.config import ResilienceConfig

logger = get_logger(__name__)


class ResilienceProvider(Provider):
    """Resilience patterns DI provider.

    Registers circuit breaker, retry, bulkhead, throttle, and rate-limiter
    infrastructure into the container as singletons.
    """

    name = "resilience"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key: str | None = "resilience"
    config_model: type | None = ResilienceConfig

    def __init__(self) -> None:
        super().__init__()
        self._registry: Any | None = None
        self._throttle_registry: Any | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register resilience services and configurations."""
        from lexigram.contracts.infra.resilience.protocols import (
            BulkheadProtocol,
            RateLimiterProtocol,
        )
        from lexigram.resilience.bulkhead.limiter import Bulkhead, BulkheadConfig
        from lexigram.resilience.circuit.breaker import CircuitBreakerRegistry
        from lexigram.resilience.rate_limiter.token_bucket import RateLimiter
        from lexigram.resilience.throttle import ThrottleRegistry

        # 1. Register Configs (Transient)
        container.transient(CircuitBreakerConfig, CircuitBreakerConfig)
        container.transient(RetryConfig, RetryConfig)

        # 2. Register Registries (Singleton)
        self._registry = CircuitBreakerRegistry()
        self._throttle_registry = ThrottleRegistry()

        container.singleton(CircuitBreakerRegistry, instance=self._registry)
        container.singleton(CircuitBreakerRegistryProtocol, instance=self._registry)
        container.singleton(ThrottleRegistry, instance=self._throttle_registry)

        # 3. Register RateLimiter (Singleton)
        # Default to 1000 rps to avoid blocking tests
        rate_limiter = RateLimiter(rate=1000)
        container.singleton(RateLimiter, instance=rate_limiter)
        container.singleton(RateLimiterProtocol, instance=rate_limiter)

        # 4. Register Bulkhead (Singleton)
        bulkhead = Bulkhead(config=BulkheadConfig())
        container.singleton(Bulkhead, instance=bulkhead)
        container.singleton(BulkheadProtocol, instance=bulkhead)

        # 5. Register ResiliencePipelineFactoryProtocol (Singleton)
        from lexigram.resilience.pipeline.executor import ResiliencePipeline

        def resilience_pipeline_factory(
            retry_config: RetryConfig,
            circuit_config: CircuitBreakerConfig,
            timeout_config: TimeoutConfig,
        ) -> ResiliencePipelineProtocol:
            return ResiliencePipeline(
                retry_config=retry_config,
                circuit_config=circuit_config,
                timeout_config=timeout_config,
            )

        container.singleton(
            ResiliencePipelineFactoryProtocol,
            factory=lambda: resilience_pipeline_factory,
        )

    async def boot(self, container: BootContainerProtocol) -> None:
        """Initialize resilience patterns on application boot."""
        from lexigram.contracts.observability.metrics import MetricsCollectorProtocol

        collector = await container.resolve_optional(MetricsCollectorProtocol)
        if (
            collector is not None
            and self._registry
            and hasattr(self._registry, "set_metrics_collector")
        ):
            self._registry.set_metrics_collector(collector)

        # Wire distributed circuit-breaker backend when configured
        from lexigram.resilience.config import ResilienceConfig

        config = await container.resolve_optional(ResilienceConfig)
        if config is not None:
            cb_backend = config.circuit_breaker.backend
            if cb_backend != "memory" and self._registry is not None:
                from lexigram.contracts import StateStoreProtocol
                from lexigram.resilience.circuit.backend import (
                    DistributedCircuitBreakerBackend,
                )

                state_store = await container.resolve_optional(StateStoreProtocol)
                if state_store is not None:
                    dist_backend = DistributedCircuitBreakerBackend(store=state_store)
                    self._registry.set_backend(dist_backend)
                    logger.info(
                        "resilience.distributed_cb_backend_wired", backend=cb_backend
                    )
                else:
                    logger.debug(
                        "resilience.distributed_cb_backend_skipped",
                        reason="StateStoreProtocol not registered",
                    )

    async def shutdown(self) -> None:
        """Cleanup resilience patterns on shutdown."""
        if self._registry and hasattr(self._registry, "cleanup"):
            self._registry.cleanup()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report resilience health."""
        total_breakers = 0
        if self._registry and hasattr(self._registry, "_breakers"):
            total_breakers = len(self._registry._breakers)

        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={"circuit_breakers": {"total": total_breakers}},
        )


__all__ = ["ResilienceProvider"]
