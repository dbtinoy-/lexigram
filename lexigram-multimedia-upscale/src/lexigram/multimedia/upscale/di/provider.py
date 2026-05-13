"""DI provider for the upscale generation subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import UpscaleProvider
from lexigram.di.provider import Provider
from lexigram.di.provider_utils import resolve_optional
from lexigram.logging import get_logger
from lexigram.multimedia.upscale.config import UpscaleConfig
from lexigram.multimedia.upscale.tasks import UpscaleTask

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
    config_key: str | None = "multimedia_upscale"
    config_model: type | None = UpscaleConfig

    def __init__(self, config: UpscaleConfig | None = None) -> None:
        super().__init__(name="upscale")
        self._requested_config = config
        self._config = config or UpscaleConfig()
        self._backend: UpscaleProvider | None = None
        self._task_handler: UpscaleTask | None = None
        self._retry: RetryPolicyProtocol | None = None
        self._circuit_breaker: CircuitBreakerProtocol | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.contracts.infra.resilience.protocols import (
            CircuitBreakerProtocol,
            RetryPolicyProtocol,
        )

        self._config = self._requested_config or self._config or UpscaleConfig()
        container.singleton(UpscaleConfig, self._config)

        self._retry = await resolve_optional(container, RetryPolicyProtocol)
        self._circuit_breaker = await resolve_optional(
            container, CircuitBreakerProtocol
        )

        if self._config.backend == "real-esrgan":
            from lexigram.multimedia.upscale.providers.real_esrgan import (
                RealEsrganUpscaleProvider,
            )

            self._backend = cast(
                "UpscaleProvider",
                RealEsrganUpscaleProvider(
                    base_url=self._config.real_esrgan_base_url,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "hat":
            from lexigram.multimedia.upscale.providers.hat import HatUpscaleProvider

            self._backend = cast(
                "UpscaleProvider",
                HatUpscaleProvider(
                    base_url=self._config.hat_base_url,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        else:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented upscale backend: {self._config.backend!r}"
            )

        assert self._backend is not None
        container.singleton(UpscaleProvider, self._backend)

        self._task_handler = UpscaleTask(backend=self._backend)
        container.singleton(UpscaleTask, self._task_handler)

        from lexigram.contracts.multimedia.protocols import VideoProcessor

        video_processor = await resolve_optional(container, VideoProcessor)
        if video_processor is not None:
            from lexigram.multimedia.upscale.video_upscale_service import (
                VideoUpscaleService,
            )

            video_upscale_service = VideoUpscaleService(
                upscale_provider=self._backend, video_processor=video_processor
            )
            container.singleton(VideoUpscaleService, video_upscale_service)

        logger.info("upscale_registered", backend=self._config.backend)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No async I/O needed at boot beyond what register() already did."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if self._backend is None:
            return HealthCheckResult(component=self.name, status=HealthStatus.UNHEALTHY)

        if self._config.backend == "real-esrgan":
            base_url = self._config.real_esrgan_base_url
        elif self._config.backend == "hat":
            base_url = self._config.hat_base_url

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
