"""Image backend registry — registry-based dispatch of image backends."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError

ImageBackendBuilder = Callable[..., Awaitable[Any]]


class ImageBackendRegistry:
    """Registry of image-backend builders, keyed by backend name.

    Usage::

        registry = ImageBackendRegistry.with_defaults()
        backend = await registry.create_backend("stability", config, secret_store, retry, cb)
    """

    def __init__(self) -> None:
        """Initialise an empty backend registry."""
        self._builders: dict[str, ImageBackendBuilder] = {}

    @classmethod
    def with_defaults(cls) -> ImageBackendRegistry:
        """Return a registry populated with the built-in image backends."""
        registry = cls()

        async def _local_http(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kw: Any,
        ) -> Any:
            from lexigram.multimedia.image.providers.local_http import (
                LocalHttpImageProvider,
            )

            return LocalHttpImageProvider(
                base_url=config.local_http_base_url,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _stability(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kw: Any,
        ) -> Any:
            from lexigram.di.provider_utils import resolve_credential
            from lexigram.multimedia.image.providers.stability import (
                StabilityImageProvider,
            )

            api_key = await resolve_credential(
                secret_store, config.stability_api_key_secret_name
            )
            return StabilityImageProvider(
                api_key=api_key or "",
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _openai(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kw: Any,
        ) -> Any:
            from lexigram.di.provider_utils import resolve_credential
            from lexigram.multimedia.image.providers.openai import OpenAIImageProvider

            api_key = await resolve_credential(
                secret_store, config.openai_api_key_secret_name
            )
            return OpenAIImageProvider(
                api_key=api_key or "",
                model=config.openai_model,
                base_url=config.openai_base_url,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _comfyui(
            config: Any,
            secret_store: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kw: Any,
        ) -> Any:
            from lexigram.multimedia.image.providers.comfyui import ComfyUiImageProvider

            return ComfyUiImageProvider(
                base_url=config.comfyui_base_url,
                checkpoint=config.comfyui_checkpoint,
                workflow_path=config.comfyui_workflow_path,
                steps=config.comfyui_steps,
                cfg_scale=config.comfyui_cfg_scale,
                poll_interval=config.comfyui_poll_interval,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        registry.register("local-http", _local_http)
        registry.register("stability", _stability)
        registry.register("openai", _openai)
        registry.register("comfyui", _comfyui)
        return registry

    def register(self, backend: str, builder: ImageBackendBuilder) -> None:
        """Register a builder under a backend name."""
        self._builders[backend] = builder

    async def create_backend(
        self,
        backend: str,
        config: Any,
        secret_store: Any,
        retry: Any,
        circuit_breaker: Any,
    ) -> Any:
        """Build an image provider for a backend name."""
        builder = self._builders.get(backend)
        if builder is None:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented image backend: {backend!r}"
            )
        return await builder(config, secret_store, retry, circuit_breaker)

    def backends(self) -> list[str]:
        """Return the registered backend names."""
        return list(self._builders.keys())

    def __contains__(self, backend: str) -> bool:
        return backend in self._builders


__all__ = ["ImageBackendBuilder", "ImageBackendRegistry"]
