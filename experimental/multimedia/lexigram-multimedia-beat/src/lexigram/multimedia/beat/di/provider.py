"""DI provider for the beat-analysis subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.protocols import BeatAnalysisProvider
from lexigram.di.provider import Provider
from lexigram.di.provider_utils import resolve_optional
from lexigram.logging import get_logger
from lexigram.multimedia.beat.backends.registry import BeatBackendRegistry
from lexigram.multimedia.beat.config import BeatAnalysisConfig

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )

logger = get_logger(__name__)

__all__ = ["BeatAnalysisGenerationProvider"]


class BeatAnalysisGenerationProvider(Provider):
    """Provider that registers a configured BeatAnalysisProvider backend."""

    name = "beat"
    config_key: str | None = "multimedia_beat"
    config_model: type | None = BeatAnalysisConfig

    def __init__(
        self,
        config: BeatAnalysisConfig | None = None,
        *,
        backend_registry: BeatBackendRegistry | None = None,
    ) -> None:
        super().__init__(name="beat")
        self._requested_config = config
        self._config = config
        self._backend_registry = backend_registry or BeatBackendRegistry.with_defaults()
        self._backend: BeatAnalysisProvider | None = None
        self._retry: RetryPolicyProtocol | None = None
        self._circuit_breaker: CircuitBreakerProtocol | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.contracts.infra.resilience.protocols import (
            CircuitBreakerProtocol,
            RetryPolicyProtocol,
        )

        self._config = self._requested_config or self._config or BeatAnalysisConfig()
        container.singleton(BeatAnalysisConfig, self._config)

        self._retry = await resolve_optional(container, RetryPolicyProtocol)
        self._circuit_breaker = await resolve_optional(container, CircuitBreakerProtocol)

        self._backend = cast(
            "BeatAnalysisProvider",
            await self._backend_registry.create_backend(
                self._config.backend,
                self._config,
                self._retry,
                self._circuit_breaker,
            ),
        )

        assert self._backend is not None  # noqa: S101
        container.singleton(BeatAnalysisProvider, self._backend)
        logger.info("beat_analysis_registered", backend=self._config.backend)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No async I/O needed at boot beyond what register() already did."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if self._backend is None:
            return HealthCheckResult(component=self.name, status=HealthStatus.UNHEALTHY)

        if self._config.backend == "librosa":
            return HealthCheckResult(component=self.name, status=HealthStatus.HEALTHY)

        import aiohttp

        try:
            async with (
                aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session,
                session.get(f"{self._config.madmom_base_url}/health") as resp,
            ):
                status = HealthStatus.HEALTHY if resp.status == 200 else HealthStatus.DEGRADED
        except (TimeoutError, OSError, aiohttp.ClientError):
            status = HealthStatus.DEGRADED
        return HealthCheckResult(component=self.name, status=status)
