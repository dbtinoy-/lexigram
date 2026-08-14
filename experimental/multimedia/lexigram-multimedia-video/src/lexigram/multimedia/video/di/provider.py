"""DI provider for the video generation subsystem."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, TypedDict, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import VideoProcessor, VideoProvider
from lexigram.di.provider import Provider
from lexigram.di.provider_utils import resolve_credential, resolve_optional
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


class _TimeoutKwargs(TypedDict, total=False):
    """Keyword arguments for backend constructor timeouts."""

    timeout: float


class VideoGenerationProvider(Provider):
    """Provider that registers a configured VideoProvider backend."""

    name = "video"
    config_key: str | None = "multimedia_video"
    config_model: type | None = VideoConfig

    def __init__(self, config: VideoConfig | None = None) -> None:
        super().__init__(name="video")
        self._requested_config = config
        self._config = config or VideoConfig()
        self._backend: VideoProvider | None = None
        self._task_handler: VideoGenerationTask | None = None
        self._processing_backend: VideoProcessor | None = None
        self._processing_task_handler: VideoProcessingTask | None = None
        self._secret_store: AsyncSecretStoreProtocol | None = None
        self._retry: RetryPolicyProtocol | None = None
        self._circuit_breaker: CircuitBreakerProtocol | None = None
        self._credential_resolved: bool = False

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.contracts.infra.resilience.protocols import (
            CircuitBreakerProtocol,
            RetryPolicyProtocol,
        )
        from lexigram.contracts.security.stores import AsyncSecretStoreProtocol

        self._config = self._requested_config or self._config or VideoConfig()
        self._timeout_kwargs: _TimeoutKwargs = (
            {"timeout": self._config.timeout}
            if self._config.timeout is not None
            else {}
        )
        container.singleton(VideoConfig, self._config)

        self._secret_store = await resolve_optional(container, AsyncSecretStoreProtocol)
        self._retry = await resolve_optional(container, RetryPolicyProtocol)
        self._circuit_breaker = await resolve_optional(
            container, CircuitBreakerProtocol
        )

        if self._config.backend == "local-http":
            from lexigram.multimedia.video.providers.local_http import (
                LocalHttpVideoProvider,
            )

            self._backend = cast(
                "VideoProvider",
                LocalHttpVideoProvider(
                    base_url=self._config.local_http_base_url,
                    **self._timeout_kwargs,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "runway":
            from lexigram.multimedia.video.providers.runway import (
                RunwayVideoProvider,
            )

            api_key = (
                await resolve_credential(
                    self._secret_store, self._config.runway_api_key_secret_name
                )
                or ""
            )
            self._credential_resolved = bool(api_key)
            self._backend = cast(
                "VideoProvider",
                RunwayVideoProvider(
                    api_key=api_key,
                    **self._timeout_kwargs,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "openai":
            from lexigram.multimedia.video.providers.openai import OpenAIVideoProvider

            api_key = (
                await resolve_credential(
                    self._secret_store, self._config.openai_api_key_secret_name
                )
                or ""
            )
            self._credential_resolved = bool(api_key)
            self._backend = cast(
                "VideoProvider",
                OpenAIVideoProvider(
                    api_key=api_key or "",
                    model=self._config.openai_model,
                    base_url=self._config.openai_base_url,
                    **self._timeout_kwargs,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "wan22":
            from lexigram.multimedia.video.providers.wan22 import Wan22VideoProvider

            self._credential_resolved = True
            self._backend = cast(
                "VideoProvider",
                Wan22VideoProvider(
                    base_url=self._config.wan22_base_url,
                    **self._timeout_kwargs,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "cogvideox":
            from lexigram.multimedia.video.providers.cogvideox import (
                CogVideoXVideoProvider,
            )

            self._credential_resolved = True
            self._backend = cast(
                "VideoProvider",
                CogVideoXVideoProvider(
                    base_url=self._config.cogvideox_base_url,
                    **self._timeout_kwargs,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "svd":
            from lexigram.multimedia.video.providers.svd import SVDVideoProvider

            self._credential_resolved = True
            self._backend = cast(
                "VideoProvider",
                SVDVideoProvider(
                    base_url=self._config.svd_base_url,
                    **self._timeout_kwargs,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "comfyui":
            from lexigram.multimedia.video.providers.comfyui import (
                ComfyUiVideoProvider,
            )

            self._credential_resolved = True
            self._backend = cast(
                "VideoProvider",
                ComfyUiVideoProvider(
                    base_url=self._config.comfyui_base_url,
                    checkpoint=self._config.comfyui_checkpoint,
                    workflow_path=self._config.comfyui_workflow_path,
                    fps=self._config.comfyui_fps,
                    motion_bucket_id=self._config.comfyui_motion_bucket_id,
                    poll_interval=self._config.comfyui_poll_interval,
                    **self._timeout_kwargs,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        else:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented video backend: {self._config.backend!r}"
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
            status=HealthStatus.HEALTHY
            if self._credential_resolved
            else HealthStatus.DEGRADED,
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
