"""Music backend registry — registry-based dispatch of music backends."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError

MusicBackendBuilder = Callable[..., Awaitable[Any]]


class MusicBackendRegistry:
    """Registry of music-backend builders, keyed by backend name.

    Usage::

        registry = MusicBackendRegistry.with_defaults()
        backend = await registry.create_backend("stability-audio", config, secret_store, retry, cb)
    """

    def __init__(self) -> None:
        """Initialise an empty backend registry."""
        self._builders: dict[str, MusicBackendBuilder] = {}

    @classmethod
    def with_defaults(cls) -> MusicBackendRegistry:
        """Return a registry populated with the built-in music backends."""
        registry = cls()

        async def _local_http(
            config: Any, secret_store: Any, retry: Any, circuit_breaker: Any, **_kw: Any,
        ) -> Any:
            from lexigram.multimedia.music.providers.local_http import (
                LocalHttpMusicProvider,
            )

            return LocalHttpMusicProvider(
                base_url=config.local_http_base_url,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _stability_audio(
            config: Any, secret_store: Any, retry: Any, circuit_breaker: Any, **_kw: Any,
        ) -> Any:
            from lexigram.di.provider_utils import resolve_credential
            from lexigram.multimedia.music.providers.stability_audio import (
                StabilityAudioMusicProvider,
            )

            api_key = await resolve_credential(secret_store, config.stability_api_key_secret_name)
            return StabilityAudioMusicProvider(
                api_key=api_key or "",
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _ace_step(
            config: Any, secret_store: Any, retry: Any, circuit_breaker: Any, **_kw: Any,
        ) -> Any:
            from lexigram.multimedia.music.providers.ace_step import (
                AceStepMusicProvider,
            )

            return AceStepMusicProvider(
                base_url=config.ace_step_base_url,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _stable_audio_open(
            config: Any, secret_store: Any, retry: Any, circuit_breaker: Any, **_kw: Any,
        ) -> Any:
            from lexigram.multimedia.music.providers.stable_audio_open import (
                StableAudioOpenMusicProvider,
            )

            return StableAudioOpenMusicProvider(
                base_url=config.stable_audio_open_base_url,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        registry.register("local-http", _local_http)
        registry.register("stability-audio", _stability_audio)
        registry.register("ace-step", _ace_step)
        registry.register("stable-audio-open", _stable_audio_open)
        return registry

    def register(self, backend: str, builder: MusicBackendBuilder) -> None:
        """Register a builder under a backend name."""
        self._builders[backend] = builder

    async def create_backend(
        self, backend: str, config: Any, secret_store: Any, retry: Any, circuit_breaker: Any,
    ) -> Any:
        """Build a music provider for a backend name."""
        builder = self._builders.get(backend)
        if builder is None:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented music backend: {backend!r}"
            )
        return await builder(config, secret_store, retry, circuit_breaker)

    def backends(self) -> list[str]:
        """Return the registered backend names."""
        return list(self._builders.keys())

    def __contains__(self, backend: str) -> bool:
        return backend in self._builders


__all__ = ["MusicBackendBuilder", "MusicBackendRegistry"]
