"""DI provider for the TTS subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.protocols import TTSProvider
from lexigram.di.provider import Provider
from lexigram.di.provider_utils import resolve_optional
from lexigram.logging import get_logger
from lexigram.multimedia.tts.backends.registry import TTSBackendRegistry
from lexigram.multimedia.tts.config import TTSConfig
from lexigram.multimedia.tts.tasks import TTSGenerationTask

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

__all__ = ["AudioTTSProvider"]


class AudioTTSProvider(Provider):
    """Provider that registers a configured TTSProvider backend."""

    name = "tts"
    config_key: str | None = "multimedia_tts"
    config_model: type | None = TTSConfig

    def __init__(
        self,
        config: TTSConfig | None = None,
        *,
        backend_registry: TTSBackendRegistry | None = None,
    ) -> None:
        super().__init__(name="tts")
        self._requested_config = config
        self._config = config
        self._backend_registry = backend_registry or TTSBackendRegistry.with_defaults()
        self._backend: TTSProvider | None = None
        self._api_keys: dict[str, str] = {}
        self._task_handler: TTSGenerationTask | None = None
        self._secret_store: AsyncSecretStoreProtocol | None = None
        self._retry: RetryPolicyProtocol | None = None
        self._circuit_breaker: CircuitBreakerProtocol | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.contracts.infra.resilience.protocols import (
            CircuitBreakerProtocol,
            RetryPolicyProtocol,
        )
        from lexigram.contracts.security.stores import AsyncSecretStoreProtocol

        self._config = self._requested_config or self._config or TTSConfig()
        container.singleton(TTSConfig, self._config)

        self._secret_store = await resolve_optional(container, AsyncSecretStoreProtocol)
        self._retry = await resolve_optional(container, RetryPolicyProtocol)
        self._circuit_breaker = await resolve_optional(
            container, CircuitBreakerProtocol
        )

        self._backend = cast(
            "TTSProvider",
            await self._backend_registry.create_backend(
                self._config.backend,
                self._config,
                self._secret_store,
                self._retry,
                self._circuit_breaker,
            ),
        )

        container.singleton(TTSProvider, self._backend)

        self._task_handler = TTSGenerationTask(backend=self._backend)
        container.singleton(TTSGenerationTask, self._task_handler)
        logger.info("tts_registered", backend=self._config.backend)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No async I/O needed at boot beyond what register() already did —
        matches AIProvider.boot() only doing optional-collaborator resolution,
        which happened above in register() here since credentials/resilience
        must be known before constructing the backend instance."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if self._backend is None:
            return HealthCheckResult(component=self.name, status=HealthStatus.UNHEALTHY)

        http_backends = {
            "local-http": self._config.local_http_base_url,
            "chatterbox": self._config.chatterbox_base_url,
            "kokoro": self._config.kokoro_base_url,
            "f5-tts": self._config.f5_tts_base_url,
            "piper": self._config.piper_base_url,
        }
        if self._config.backend in http_backends:
            status = await self._check_http_health(
                http_backends[self._config.backend], timeout
            )
            return HealthCheckResult(component=self.name, status=status)

        # API backends: credentials resolved at construction time.
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
        )

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
