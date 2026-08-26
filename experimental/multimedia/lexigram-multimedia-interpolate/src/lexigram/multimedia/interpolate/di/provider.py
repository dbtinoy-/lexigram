"""DI provider for the interpolation subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import InterpolationProvider
from lexigram.di.provider import Provider
from lexigram.di.provider_utils import resolve_optional
from lexigram.logging import get_logger
from lexigram.multimedia.interpolate.config import InterpolationConfig
from lexigram.multimedia.interpolate.tasks import InterpolationTask

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )
    from lexigram.multimedia.interpolate.video_interpolation_service import (
        VideoInterpolationService,
    )

logger = get_logger(__name__)

__all__ = ["InterpolationGenerationProvider"]


class InterpolationGenerationProvider(Provider):
    """Provider that registers a configured InterpolationProvider backend."""

    name = "interpolate"
    config_key: str | None = "multimedia_interpolate"
    config_model: type | None = InterpolationConfig

    def __init__(self, config: InterpolationConfig | None = None) -> None:
        super().__init__(name="interpolate")
        self._requested_config = config
        # No default baking: the orchestrator injects the yaml section into
        # ``provider.config`` after construction, before ``register()``.
        self._config = config
        self._backend: InterpolationProvider | None = None
        self._task_handler: InterpolationTask | None = None
        self._retry: RetryPolicyProtocol | None = None
        self._circuit_breaker: CircuitBreakerProtocol | None = None
        self._video_interpolation_service: VideoInterpolationService | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.contracts.infra.resilience.protocols import (
            CircuitBreakerProtocol,
            RetryPolicyProtocol,
        )

        self._config = self._requested_config or self._config or InterpolationConfig()
        container.singleton(InterpolationConfig, self._config)

        self._retry = await resolve_optional(container, RetryPolicyProtocol)
        self._circuit_breaker = await resolve_optional(
            container, CircuitBreakerProtocol
        )

        if self._config.backend == "rife":
            from lexigram.multimedia.interpolate.providers.rife import (
                RifeInterpolationProvider,
            )

            self._backend = cast(
                "InterpolationProvider",
                RifeInterpolationProvider(
                    base_url=self._config.rife_base_url,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        else:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented interpolation backend: "
                f"{self._config.backend!r}"
            )

        assert self._backend is not None  # noqa: S101  # raised via ProviderNotInstalledError above
        container.singleton(InterpolationProvider, self._backend)

        self._task_handler = InterpolationTask(backend=self._backend)
        container.singleton(InterpolationTask, self._task_handler)

        from lexigram.contracts.multimedia.protocols import VideoProcessor

        video_processor = await resolve_optional(container, VideoProcessor)
        if video_processor is not None:
            from lexigram.multimedia.interpolate.video_interpolation_service import (
                VideoInterpolationService,
            )

            video_interpolation_service = VideoInterpolationService(
                interpolation_provider=self._backend, video_processor=video_processor
            )
            self._video_interpolation_service = video_interpolation_service
            container.singleton(VideoInterpolationService, video_interpolation_service)

        logger.info("interpolation_registered", backend=self._config.backend)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No async I/O needed at boot beyond what register() already did."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if self._backend is None:
            return HealthCheckResult(component=self.name, status=HealthStatus.UNHEALTHY)

        if self._config.backend == "rife":
            base_url = self._config.rife_base_url

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
