"""DI provider for the TTS subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import TTSProvider
from lexigram.di.provider import Provider
from lexigram.di.provider_utils import resolve_credential, resolve_optional
from lexigram.logging import get_logger
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

    def __init__(self, config: TTSConfig | None = None) -> None:
        super().__init__(name="tts")
        self._requested_config = config
        # No default baking: the orchestrator injects the yaml section into
        # ``provider.config`` after construction, before ``register()``.
        self._config = config
        self._backend: TTSProvider | None = None
        self._elevenlabs_api_key: str | None = None
        self._openai_api_key: str | None = None
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

        if self._config.backend == "local-http":
            from lexigram.multimedia.tts.providers.local_http import (
                LocalHttpTTSProvider,
            )

            self._backend = cast(
                "TTSProvider",
                LocalHttpTTSProvider(
                    base_url=self._config.local_http_base_url,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "elevenlabs":
            try:
                from lexigram.multimedia.tts.providers.elevenlabs import (
                    ElevenLabsTTSProvider,
                )
            except ImportError as exc:
                raise ProviderNotInstalledError(
                    "ElevenLabs backend selected but its extra is not installed. "
                    "Install: pip install lexigram-multimedia-tts[elevenlabs]"
                ) from exc

            api_key = await resolve_credential(
                self._secret_store, self._config.elevenlabs_api_key_secret_name
            )
            self._elevenlabs_api_key = api_key
            if not self._config.elevenlabs_voice_id:
                raise ProviderNotInstalledError(
                    "TTSConfig.elevenlabs_voice_id is required when backend='elevenlabs'"
                )
            self._backend = cast(
                "TTSProvider",
                ElevenLabsTTSProvider(
                    api_key=api_key or "",
                    voice_id=self._config.elevenlabs_voice_id,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "openai":
            from lexigram.multimedia.tts.providers.openai import OpenAITTSProvider

            api_key = await resolve_credential(
                self._secret_store, self._config.openai_api_key_secret_name
            )
            self._openai_api_key = api_key
            self._backend = cast(
                "TTSProvider",
                OpenAITTSProvider(
                    api_key=api_key or "",
                    voice=self._config.openai_voice,
                    model=self._config.openai_model,
                    base_url=self._config.openai_base_url,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "chatterbox":
            from lexigram.multimedia.tts.providers.chatterbox import (
                ChatterboxTTSProvider,
            )

            self._backend = cast(
                "TTSProvider",
                ChatterboxTTSProvider(
                    base_url=self._config.chatterbox_base_url,
                    exaggeration=self._config.chatterbox_exaggeration,
                    cfg_weight=self._config.chatterbox_cfg_weight,
                    temperature=self._config.chatterbox_temperature,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "kokoro":
            from lexigram.multimedia.tts.providers.kokoro import KokoroTTSProvider

            self._backend = cast(
                "TTSProvider",
                KokoroTTSProvider(
                    base_url=self._config.kokoro_base_url,
                    default_voice=self._config.kokoro_default_voice,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "f5-tts":
            from lexigram.multimedia.tts.providers.f5_tts import F5TTSProvider

            self._backend = cast(
                "TTSProvider",
                F5TTSProvider(
                    base_url=self._config.f5_tts_base_url,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        elif self._config.backend == "piper":
            from lexigram.multimedia.tts.providers.piper import PiperTTSProvider

            self._backend = cast(
                "TTSProvider",
                PiperTTSProvider(
                    base_url=self._config.piper_base_url,
                    default_voice=self._config.piper_default_voice,
                    timeout=self._config.timeout,
                    retry=self._retry,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        else:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented TTS backend: {self._config.backend!r}"
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

        # API backends: verify credentials are present, never make a billed call.
        has_key = bool(
            self._elevenlabs_api_key
            if self._config.backend == "elevenlabs"
            else self._openai_api_key
            if self._config.backend == "openai"
            else True
        )
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY if has_key else HealthStatus.DEGRADED,
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
