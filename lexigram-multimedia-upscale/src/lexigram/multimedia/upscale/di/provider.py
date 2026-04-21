"""DI provider for the upscale generation subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import UpscaleProvider
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.multimedia.upscale.config import UpscaleConfig

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

__all__ = ["UpscaleGenerationProvider"]


class UpscaleGenerationProvider(Provider):
    """Provider that registers a configured UpscaleProvider backend."""

    name = "upscale"

    def __init__(self, config: UpscaleConfig | None = None) -> None:
        super().__init__(name="upscale")
        self._upscale_config = config or UpscaleConfig()
        self._backend: UpscaleProvider | None = None
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

        if self._upscale_config.backend == "real-esrgan":
            from lexigram.multimedia.upscale.providers.real_esrgan import (
                RealEsrganUpscaleProvider,
            )

            self._backend = cast(
                "UpscaleProvider",
                RealEsrganUpscaleProvider(
                    base_url=self._upscale_config.real_esrgan_base_url,
                    timeout=self._upscale_config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        else:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented upscale backend: {self._upscale_config.backend!r}"
            )

        assert self._backend is not None
        container.singleton(UpscaleProvider, self._backend)
        logger.info("upscale_registered", backend=self._upscale_config.backend)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No async I/O needed at boot beyond what register() already did."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if self._backend is None:
            return HealthCheckResult(component=self.name, status=HealthStatus.UNHEALTHY)

        base_url = None
        if self._upscale_config.backend == "real-esrgan":
            base_url = self._upscale_config.real_esrgan_base_url

        if base_url is not None:
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

        return HealthCheckResult(component=self.name, status=HealthStatus.HEALTHY)
