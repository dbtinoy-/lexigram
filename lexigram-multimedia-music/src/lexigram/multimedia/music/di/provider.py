"""DI provider for the music generation subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import MusicProvider
from lexigram.di.provider import Provider
from lexigram.di.provider_utils import resolve_optional
from lexigram.logging import get_logger
from lexigram.multimedia.music.config import MusicConfig
from lexigram.multimedia.music.tasks import MusicGenerationTask

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

__all__ = ["AudioMusicProvider"]


class AudioMusicProvider(Provider):
    """Provider that registers a configured MusicProvider backend."""

    name = "music"
    config_key: str | None = "multimedia_music"
    config_model: type | None = MusicConfig

    def __init__(self, config: MusicConfig | None = None) -> None:
        super().__init__(name="music")
        self._requested_config = config
        self._config = config or MusicConfig()
        self._backend: MusicProvider | None = None
        self._task_handler: MusicGenerationTask | None = None
        self._secret_store: AsyncSecretStoreProtocol | None = None
        self._retry: RetryPolicyProtocol | None = None
        self._circuit_breaker: CircuitBreakerProtocol | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.contracts.infra.resilience.protocols import (
            CircuitBreakerProtocol,
            RetryPolicyProtocol,
        )
        from lexigram.contracts.security.stores import AsyncSecretStoreProtocol

        self._config = self._requested_config or self._config or MusicConfig()
        container.singleton(MusicConfig, self._config)

        self._secret_store = await resolve_optional(container, AsyncSecretStoreProtocol)
        self._retry = await resolve_optional(container, RetryPolicyProtocol)
        self._circuit_breaker = await resolve_optional(
            container, CircuitBreakerProtocol
        )

        if self._config.backend == "local-http":
            from lexigram.multimedia.music.providers.local_http import (
                LocalHttpMusicProvider,
            )

            self._backend = cast(
                "MusicProvider",
                LocalHttpMusicProvider(
                    base_url=self._config.local_http_base_url,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "stability-audio":
            raise ProviderNotInstalledError(
                "backend='stability-audio' is not yet implemented in "
                "lexigram-multimedia-music. Use backend='local-http' or "
                "contribute an implementation."
            )
        elif self._config.backend == "ace-step":
            from lexigram.multimedia.music.providers.ace_step import (
                AceStepMusicProvider,
            )

            self._backend = cast(
                "MusicProvider",
                AceStepMusicProvider(
                    base_url=self._config.ace_step_base_url,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "stable-audio-open":
            from lexigram.multimedia.music.providers.stable_audio_open import (
                StableAudioOpenMusicProvider,
            )

            self._backend = cast(
                "MusicProvider",
                StableAudioOpenMusicProvider(
                    base_url=self._config.stable_audio_open_base_url,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        else:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented music backend: {self._config.backend!r}"
            )

        assert self._backend is not None
        container.singleton(MusicProvider, self._backend)

        self._task_handler = MusicGenerationTask(backend=self._backend)
        container.singleton(MusicGenerationTask, self._task_handler)
        logger.info("music_registered", backend=self._config.backend)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No async I/O needed at boot beyond what register() already did."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if self._backend is None:
            return HealthCheckResult(component=self.name, status=HealthStatus.UNHEALTHY)

        http_backends = {
            "local-http": self._config.local_http_base_url,
            "ace-step": self._config.ace_step_base_url,
            "stable-audio-open": self._config.stable_audio_open_base_url,
        }
        if self._config.backend in http_backends:
            status = await self._check_http_health(
                http_backends[self._config.backend], timeout
            )
            return HealthCheckResult(component=self.name, status=status)

        return HealthCheckResult(component=self.name, status=HealthStatus.HEALTHY)

    async def _check_http_health(self, base_url: str, timeout: float) -> HealthStatus:
        import aiohttp

        try:
            async with (
                aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as session,
                session.get(f"{base_url}/health") as resp,
            ):
                return (
                    HealthStatus.HEALTHY
                    if resp.status == 200
                    else HealthStatus.DEGRADED
                )
        except (TimeoutError, OSError, aiohttp.ClientError):
            return HealthStatus.DEGRADED
