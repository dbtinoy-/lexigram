"""DI provider for the interpolation subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import InterpolationProvider
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.multimedia.interpolate.config import InterpolationConfig

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

__all__ = ["InterpolationGenerationProvider"]


class InterpolationGenerationProvider(Provider):
    """Provider that registers a configured InterpolationProvider backend."""

    name = "interpolate"

    def __init__(self, config: InterpolationConfig | None = None) -> None:
        super().__init__(name="interpolate")
        self._interpolation_config = config or InterpolationConfig()
        self._backend: InterpolationProvider | None = None
        self._retry: RetryPolicyProtocol | None = None
        self._circuit_breaker: CircuitBreakerProtocol | None = None

    async def _resolve_optional(self, container: Any, protocol: type) -> Any:
        resolver = getattr(container, "resolve_optional", None)
        if resolver is not None:
            return await resolver(protocol)
        try:
            return await container.resolve(protocol)
        except (LookupError, KeyError, ValueError, TypeError):
            return None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.contracts.infra.resilience.protocols import (
            CircuitBreakerProtocol,
            RetryPolicyProtocol,
        )

        self._retry = await self._resolve_optional(container, RetryPolicyProtocol)
        self._circuit_breaker = await self._resolve_optional(
            container, CircuitBreakerProtocol
        )

        if self._interpolation_config.backend == "rife":
            from lexigram.multimedia.interpolate.providers.rife import (
                RifeInterpolationProvider,
            )

            self._backend = cast(
                "InterpolationProvider",
                RifeInterpolationProvider(
                    base_url=self._interpolation_config.rife_base_url,
                    timeout=self._interpolation_config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        else:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented interpolation backend: "
                f"{self._interpolation_config.backend!r}"
            )

        assert self._backend is not None
        container.singleton(InterpolationProvider, self._backend)
        logger.info(
            "interpolation_registered", backend=self._interpolation_config.backend
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No async I/O needed at boot beyond what register() already did."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if self._backend is None:
            return HealthCheckResult(component=self.name, status=HealthStatus.UNHEALTHY)

        if self._interpolation_config.backend == "rife":
            base_url = self._interpolation_config.rife_base_url

        import aiohttp

        try:
            async with (
                aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as session,
                session.get(f"{base_url}/health") as resp,
            ):
                status = (
                    HealthStatus.HEALTHY
                    if resp.status == 200
                    else HealthStatus.DEGRADED
                )
        except (TimeoutError, OSError, aiohttp.ClientError):
            status = HealthStatus.DEGRADED
        return HealthCheckResult(component=self.name, status=status)
