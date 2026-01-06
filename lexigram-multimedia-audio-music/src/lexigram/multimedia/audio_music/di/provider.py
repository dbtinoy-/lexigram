"""DI provider for the music generation subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import MusicProvider
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.multimedia.audio_music.config import MusicConfig
from lexigram.multimedia.audio_music.tasks import MusicGenerationTask

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

    name = "audio-music"

    def __init__(self, config: MusicConfig | None = None) -> None:
        super().__init__(name="audio-music")
        self._music_config = config or MusicConfig()
        self._backend: MusicProvider | None = None
        self._task_handler: MusicGenerationTask | None = None
        self._secret_store: AsyncSecretStoreProtocol | None = None
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
        from lexigram.contracts.security.stores import AsyncSecretStoreProtocol

        self._secret_store = await self._resolve_optional(
            container, AsyncSecretStoreProtocol
        )
        self._retry = await self._resolve_optional(container, RetryPolicyProtocol)
        self._circuit_breaker = await self._resolve_optional(
            container, CircuitBreakerProtocol
        )

        if self._music_config.backend == "local-http":
            from lexigram.multimedia.audio_music.providers.local_http import (
                LocalHttpMusicProvider,
            )

            self._backend = cast(
                "MusicProvider",
                LocalHttpMusicProvider(
                    base_url=self._music_config.local_http_base_url,
                    timeout=self._music_config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._music_config.backend == "stability-audio":
            from lexigram.multimedia.audio_music.providers.stability_audio import (
                StabilityAudioMusicProvider,
            )

            StabilityAudioMusicProvider()
        else:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented music backend: {self._music_config.backend!r}"
            )

        assert self._backend is not None
        container.singleton(MusicProvider, self._backend)

        self._task_handler = MusicGenerationTask(backend=self._backend)
        container.singleton(MusicGenerationTask, self._task_handler)
        logger.info("audio_music_registered", backend=self._music_config.backend)

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

        if self._music_config.backend == "local-http":
            import aiohttp

            try:
                async with (
                    aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as session,
                    session.get(
                        f"{self._music_config.local_http_base_url}/health"
                    ) as resp,
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
