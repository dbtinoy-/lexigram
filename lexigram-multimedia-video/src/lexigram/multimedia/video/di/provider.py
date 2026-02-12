"""DI provider for the video generation subsystem."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import VideoProcessor, VideoProvider
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
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

    def __init__(self, config: VideoConfig | None = None) -> None:
        super().__init__(name="video")
        self._video_config = config or VideoConfig()
        self._backend: VideoProvider | None = None
        self._task_handler: VideoGenerationTask | None = None
        self._processing_backend: VideoProcessor | None = None
        self._processing_task_handler: VideoProcessingTask | None = None
        self._secret_store: AsyncSecretStoreProtocol | None = None
        self._retry: RetryPolicyProtocol | None = None
        self._circuit_breaker: CircuitBreakerProtocol | None = None
        self._credential_resolved: bool = False

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
        from lexigram.contracts.security.stores import AsyncSecretStoreProtocol

        self._secret_store = await self._resolve_optional(
            container, AsyncSecretStoreProtocol
        )
        self._retry = await self._resolve_optional(container, RetryPolicyProtocol)
        self._circuit_breaker = await self._resolve_optional(
            container, CircuitBreakerProtocol
        )

        if self._video_config.backend == "local-http":
            from lexigram.multimedia.video.providers.local_http import (
                LocalHttpVideoProvider,
            )

            self._backend = cast(
                "VideoProvider",
                LocalHttpVideoProvider(
                    base_url=self._video_config.local_http_base_url,
                    timeout=self._video_config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._video_config.backend == "runway":
            from lexigram.multimedia.video.providers.runway import (
                RunwayVideoProvider,
            )

            api_key = (
                await self._resolve_credential(
                    self._video_config.runway_api_key_secret_name
                )
                or ""
            )
            self._credential_resolved = bool(api_key)
            self._backend = cast(
                "VideoProvider",
                RunwayVideoProvider(
                    api_key=api_key,
                    timeout=self._video_config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._video_config.backend == "openai":
            from lexigram.multimedia.video.providers.openai import OpenAIVideoProvider

            api_key = (
                await self._resolve_credential(
                    self._video_config.openai_api_key_secret_name
                )
                or ""
            )
            self._credential_resolved = bool(api_key)
            self._backend = cast(
                "VideoProvider",
                OpenAIVideoProvider(
                    api_key=api_key or "",
                    model=self._video_config.openai_model,
                    base_url=self._video_config.openai_base_url,
                    timeout=self._video_config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._video_config.backend == "wan22":
            from lexigram.multimedia.video.providers.wan22 import Wan22VideoProvider

            self._credential_resolved = True
            self._backend = cast(
                "VideoProvider",
                Wan22VideoProvider(
                    base_url=self._video_config.wan22_base_url,
                    timeout=self._video_config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        else:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented video backend: {self._video_config.backend!r}"
            )

        assert self._backend is not None
        container.singleton(VideoProvider, self._backend)

        self._task_handler = VideoGenerationTask(backend=self._backend)
        container.singleton(VideoGenerationTask, self._task_handler)

        if shutil.which(self._video_config.processing.ffmpeg_binary) is None:
            raise ProviderNotInstalledError(
                "ffmpeg not found on PATH — install it: `apt install ffmpeg` / `brew install ffmpeg`"
            )
        processing_backend: VideoProcessor = cast(
            "VideoProcessor",
            FFmpegVideoProcessor(config=self._video_config.processing),
        )
        self._processing_backend = processing_backend
        container.singleton(VideoProcessor, processing_backend)
        self._processing_task_handler = VideoProcessingTask(backend=processing_backend)
        container.singleton(VideoProcessingTask, self._processing_task_handler)
        logger.info("video_registered", backend=self._video_config.backend)

    async def _resolve_credential(self, secret_name: str) -> str | None:
        """Resolve a provider API key via AsyncSecretStoreProtocol if bound,
        falling back to a plain environment variable when no secret store
        is configured.
        """
        if self._secret_store is not None:
            value = await self._secret_store.get(secret_name)
            if value:
                return value
        import os

        return os.environ.get(secret_name.upper())

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No async I/O needed at boot beyond what register() already did."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if self._backend is None:
            return HealthCheckResult(component=self.name, status=HealthStatus.UNHEALTHY)

        http_backends = {
            "local-http": self._video_config.local_http_base_url,
            "wan22": self._video_config.wan22_base_url,
            "cogvideox": self._video_config.cogvideox_base_url,
            "svd": self._video_config.svd_base_url,
            "comfyui": self._video_config.comfyui_base_url,
        }
        if self._video_config.backend in http_backends:
            status = await self._check_http_health(
                http_backends[self._video_config.backend], timeout
            )
            return HealthCheckResult(component=self.name, status=status)

        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY
            if self._credential_resolved
            else HealthStatus.DEGRADED,
        )

    async def _check_http_health(self, base_url: str, timeout: float) -> HealthStatus:
        import aiohttp

        endpoint = (
            "/system_stats"
            if base_url == self._video_config.comfyui_base_url
            else "/health"
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
