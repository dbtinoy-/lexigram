"""TTS backend registry — registry-based dispatch of TTS backends."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError

TTSBackendBuilder = Callable[..., Awaitable[Any]]


class TTSBackendRegistry:
    """Registry of TTS-backend builders, keyed by backend name.

    Each backend name maps to an async builder that constructs the
    corresponding TTS provider from config and shared collaborators
    (secret store, retry policy, circuit breaker).

    Usage::

        registry = TTSBackendRegistry.with_defaults()
        backend = await registry.create_backend("openai", config, secret_store, retry, cb)
    """

    def __init__(self) -> None:
        """Initialise an empty backend registry."""
        self._builders: dict[str, TTSBackendBuilder] = {}

    @classmethod
    def with_defaults(cls) -> TTSBackendRegistry:
        """Return a registry populated with the built-in TTS backends.

        Returns:
            A :class:`TTSBackendRegistry` pre-registered for local-http,
            elevenlabs, openai, chatterbox, kokoro, f5-tts, and piper.
        """
        registry = cls()

        async def _local_http(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            from lexigram.multimedia.tts.providers.local_http import (
                LocalHttpTTSProvider,
            )

            return LocalHttpTTSProvider(
                base_url=config.local_http_base_url,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _elevenlabs(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            try:
                from lexigram.multimedia.tts.providers.elevenlabs import (
                    ElevenLabsTTSProvider,
                )
            except ImportError as exc:
                raise ProviderNotInstalledError(
                    "ElevenLabs backend selected but its extra is not installed. "
                    "Install: pip install lexigram-multimedia-tts[elevenlabs]"
                ) from exc

            from lexigram.di.provider_utils import resolve_credential

            api_key = await resolve_credential(
                secret_store, config.elevenlabs_api_key_secret_name
            )
            if not config.elevenlabs_voice_id:
                raise ProviderNotInstalledError(
                    "TTSConfig.elevenlabs_voice_id is required when backend='elevenlabs'"
                )
            return ElevenLabsTTSProvider(
                api_key=api_key or "",
                voice_id=config.elevenlabs_voice_id,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _openai(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            from lexigram.di.provider_utils import resolve_credential
            from lexigram.multimedia.tts.providers.openai import OpenAITTSProvider

            api_key = await resolve_credential(
                secret_store, config.openai_api_key_secret_name
            )
            return OpenAITTSProvider(
                api_key=api_key or "",
                voice=config.openai_voice,
                model=config.openai_model,
                base_url=config.openai_base_url,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _chatterbox(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            from lexigram.multimedia.tts.providers.chatterbox import (
                ChatterboxTTSProvider,
            )

            return ChatterboxTTSProvider(
                base_url=config.chatterbox_base_url,
                exaggeration=config.chatterbox_exaggeration,
                cfg_weight=config.chatterbox_cfg_weight,
                temperature=config.chatterbox_temperature,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _kokoro(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            from lexigram.multimedia.tts.providers.kokoro import KokoroTTSProvider

            return KokoroTTSProvider(
                base_url=config.kokoro_base_url,
                default_voice=config.kokoro_default_voice,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _f5_tts(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            from lexigram.multimedia.tts.providers.f5_tts import F5TTSProvider

            return F5TTSProvider(
                base_url=config.f5_tts_base_url,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _piper(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            from lexigram.multimedia.tts.providers.piper import PiperTTSProvider

            return PiperTTSProvider(
                base_url=config.piper_base_url,
                default_voice=config.piper_default_voice,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        registry.register("local-http", _local_http)
        registry.register("elevenlabs", _elevenlabs)
        registry.register("openai", _openai)
        registry.register("chatterbox", _chatterbox)
        registry.register("kokoro", _kokoro)
        registry.register("f5-tts", _f5_tts)
        registry.register("piper", _piper)
        return registry

    def register(self, backend: str, builder: TTSBackendBuilder) -> None:
        """Register a builder under a backend name.

        Args:
            backend: Backend name (e.g. ``"openai"``).
            builder: Async callable ``(config, secret_store, retry, circuit_breaker) -> TTSProvider``.
        """
        self._builders[backend] = builder

    async def create_backend(
        self,
        backend: str,
        config: Any,
        secret_store: Any,
        retry: Any,
        circuit_breaker: Any,
    ) -> Any:
        """Build a TTS provider for a backend name.

        Args:
            backend: Backend name to dispatch on.
            config: TTSConfig used to construct the backend.
            secret_store: Optional secret store for credential resolution.
            retry: Optional retry policy.
            circuit_breaker: Optional circuit breaker.

        Returns:
            An instantiated TTS provider.

        Raises:
            ProviderNotInstalledError: If *backend* is not registered.
        """
        builder = self._builders.get(backend)
        if builder is None:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented TTS backend: {backend!r}"
            )
        return await builder(config, secret_store, retry, circuit_breaker)

    def backends(self) -> list[str]:
        """Return the registered backend names.

        Returns:
            List of backend names in registration order.
        """
        return list(self._builders.keys())

    def __contains__(self, backend: str) -> bool:
        return backend in self._builders


__all__ = ["TTSBackendBuilder", "TTSBackendRegistry"]
