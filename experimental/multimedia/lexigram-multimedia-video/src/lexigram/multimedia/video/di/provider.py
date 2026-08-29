"""DI provider for the video generation subsystem."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.protocols import VideoProcessor, VideoProvider
from lexigram.di.provider import Provider
from lexigram.di.provider_utils import resolve_optional
from lexigram.logging import get_logger
from lexigram.multimedia.video.backends.registry import VideoBackendRegistry
from lexigram.multimedia.video.config import VideoConfig
from lexigram.multimedia.video.processing.ffmpeg import FFmpegVideoProcessor
from lexigram.multimedia.video.tasks import (
    VideoGenerationTask,
    VideoProcessingTask,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )
    from lexigram.contracts.security.stores import AsyncSecretStoreProtocol

logger = get_logger(__name__)

__all__ = ["VideoGenerationProvider"]


class VideoGenerationProvider(Provider):
    """Provider that registers a configured VideoProvider backend."""

    name = "video"
    config_key: str | None = "multimedia_video"
    config_model: type | None = VideoConfig

    def __init__(
        self,
        config: VideoConfig | None = None,
        *,
        backend_registry: VideoBackendRegistry | None = None,
    ) -> None:
        super().__init__(name="video")
        self._requested_config = config
        self._config = config
        self._backend_registry = (
            backend_registry or VideoBackendRegistry.with_defaults()
        )
        self._backend: VideoProvider | None = None
        self._task_handler: VideoGenerationTask | None = None
        self._processing_backend: VideoProcessor | None = None
        self._processing_task_handler: VideoProcessingTask | None = None
        self._secret_store: AsyncSecretStoreProtocol | None = None
        self._retry: RetryPolicyProtocol | None = None
        self._circuit_breaker: CircuitBreakerProtocol | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.contracts.infra.resilience.protocols import (
            CircuitBreakerProtocol,
            RetryPolicyProtocol,
        )
        from lexigram.contracts.security.stores import AsyncSecretStoreProtocol

        self._config = self._requested_config or self._config or VideoConfig()
        container.singleton(VideoConfig, self._config)

        self._secret_store = await resolve_optional(container, AsyncSecretStoreProtocol)
        self._retry = await resolve_optional(container, RetryPolicyProtocol)
        self._circuit_breaker = await resolve_optional(
            container, CircuitBreakerProtocol
        )

        self._backend = cast(
            "VideoProvider",
            await self._backend_registry.create_backend(
                self._config.backend,
                self._config,
                self._secret_store,
                self._retry,
                self._circuit_breaker,
            ),
        )

        assert self._backend is not None  # noqa: S101  # raised via ProviderNotInstalledError above
        container.singleton(VideoProvider, self._backend)

        self._task_handler = VideoGenerationTask(backend=self._backend)
        container.singleton(VideoGenerationTask, self._task_handler)

        if shutil.which(self._config.processing.ffmpeg_binary) is not None:
            processing_backend: VideoProcessor = cast(
                "VideoProcessor",
                FFmpegVideoProcessor(config=self._config.processing),
            )
            self._processing_backend = processing_backend
            container.singleton(VideoProcessor, processing_backend)
            self._processing_task_handler = VideoProcessingTask(
                backend=processing_backend
            )
            container.singleton(VideoProcessingTask, self._processing_task_handler)
        else:
            logger.warning(
                "video_processing_disabled",
                reason=f"ffmpeg binary {self._config.processing.ffmpeg_binary!r} not found on PATH",
            )
        logger.info("video_registered", backend=self._config.backend)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No async I/O needed at boot beyond what register() already did."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if self._backend is None:
            return HealthCheckResult(component=self.name, status=HealthStatus.UNHEALTHY)

        http_backends = {
            "local-http": self._config.local_http_base_url,
            "wan22": self._config.wan22_base_url,
            "cogvideox": self._config.cogvideox_base_url,
            "svd": self._config.svd_base_url,
            "comfyui": self._config.comfyui_base_url,
        }
        if self._config.backend in http_backends:
            status = await self._check_http_health(
                http_backends[self._config.backend], timeout
            )
            return HealthCheckResult(component=self.name, status=status)

        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
        )

    async def _check_http_health(self, base_url: str, timeout: float) -> HealthStatus:
        import aiohttp

        endpoint = (
            "/system_stats" if base_url == self._config.comfyui_base_url else "/health"
        )
        try:
            async with (
                aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as session,
                session.get(f"{base_url}{endpoint}") as resp,
            ):
                return (
                    HealthStatus.HEALTHY
                    if resp.status == 200
                    else HealthStatus.DEGRADED
                )
        except (TimeoutError, OSError, aiohttp.ClientError):
            return HealthStatus.DEGRADED
