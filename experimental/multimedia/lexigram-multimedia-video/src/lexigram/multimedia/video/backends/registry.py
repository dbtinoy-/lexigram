"""Video backend registry — registry-based dispatch of video backends."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError

VideoBackendBuilder = Callable[..., Awaitable[Any]]


class VideoBackendRegistry:
    """Registry of video-backend builders, keyed by backend name.

    Each backend name maps to an async builder that constructs the
    corresponding video provider from config and shared collaborators
    (secret store, retry policy, circuit breaker).

    Usage::

        registry = VideoBackendRegistry.with_defaults()
        backend = await registry.create_backend("runway", config, secret_store, retry, cb)
    """

    def __init__(self) -> None:
        """Initialise an empty backend registry."""
        self._builders: dict[str, VideoBackendBuilder] = {}

    @classmethod
    def with_defaults(cls) -> VideoBackendRegistry:
        """Return a registry populated with the built-in video backends.

        Returns:
            A :class:`VideoBackendRegistry` pre-registered for local-http,
            runway, openai, wan22, cogvideox, svd, and comfyui.
        """
        registry = cls()

        def _timeout_kwargs(config: Any) -> dict[str, Any]:
            if config.timeout is not None:
                return {"timeout": config.timeout}
            return {}

        async def _local_http(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            from lexigram.multimedia.video.providers.local_http import (
                LocalHttpVideoProvider,
            )

            return LocalHttpVideoProvider(
                base_url=config.local_http_base_url,
                **_timeout_kwargs(config),
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _runway(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            from lexigram.di.provider_utils import resolve_credential
            from lexigram.multimedia.video.providers.runway import (
                RunwayVideoProvider,
            )

            api_key = (
                await resolve_credential(secret_store, config.runway_api_key_secret_name)
                or ""
            )
            return RunwayVideoProvider(
                api_key=api_key,
                **_timeout_kwargs(config),
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
            from lexigram.multimedia.video.providers.openai import OpenAIVideoProvider

            api_key = (
                await resolve_credential(secret_store, config.openai_api_key_secret_name)
                or ""
            )
            return OpenAIVideoProvider(
                api_key=api_key or "",
                model=config.openai_model,
                base_url=config.openai_base_url,
                **_timeout_kwargs(config),
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _wan22(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            from lexigram.multimedia.video.providers.wan22 import Wan22VideoProvider

            return Wan22VideoProvider(
                base_url=config.wan22_base_url,
                **_timeout_kwargs(config),
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _cogvideox(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            from lexigram.multimedia.video.providers.cogvideox import (
                CogVideoXVideoProvider,
            )

            return CogVideoXVideoProvider(
                base_url=config.cogvideox_base_url,
                **_timeout_kwargs(config),
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _svd(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            from lexigram.multimedia.video.providers.svd import SVDVideoProvider

            return SVDVideoProvider(
                base_url=config.svd_base_url,
                **_timeout_kwargs(config),
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _comfyui(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kwargs: Any,
        ) -> Any:
            from lexigram.multimedia.video.providers.comfyui import (
                ComfyUiVideoProvider,
            )

            return ComfyUiVideoProvider(
                base_url=config.comfyui_base_url,
                checkpoint=config.comfyui_checkpoint,
                workflow_path=config.comfyui_workflow_path,
                fps=config.comfyui_fps,
                motion_bucket_id=config.comfyui_motion_bucket_id,
                poll_interval=config.comfyui_poll_interval,
                **_timeout_kwargs(config),
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        registry.register("local-http", _local_http)
        registry.register("runway", _runway)
        registry.register("openai", _openai)
        registry.register("wan22", _wan22)
        registry.register("cogvideox", _cogvideox)
        registry.register("svd", _svd)
        registry.register("comfyui", _comfyui)
        return registry

    def register(self, backend: str, builder: VideoBackendBuilder) -> None:
        """Register a builder under a backend name.

        Args:
            backend: Backend name (e.g. ``"runway"``).
            builder: Async callable ``(config, secret_store, retry, circuit_breaker) -> VideoProvider``.
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
        """Build a video provider for a backend name.

        Args:
            backend: Backend name to dispatch on.
            config: VideoConfig used to construct the backend.
            secret_store: Optional secret store for credential resolution.
            retry: Optional retry policy.
            circuit_breaker: Optional circuit breaker.

        Returns:
            An instantiated video provider.

        Raises:
            ProviderNotInstalledError: If *backend* is not registered.
        """
        builder = self._builders.get(backend)
        if builder is None:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented video backend: {backend!r}"
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


__all__ = ["VideoBackendBuilder", "VideoBackendRegistry"]
