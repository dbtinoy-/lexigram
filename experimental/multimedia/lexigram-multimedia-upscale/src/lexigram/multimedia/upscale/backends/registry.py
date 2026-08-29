"""Upscale backend registry — registry-based dispatch of upscale backends."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError

UpscaleBackendBuilder = Callable[..., Awaitable[Any]]


class UpscaleBackendRegistry:
    """Registry of upscale-backend builders, keyed by backend name.

    Usage::

        registry = UpscaleBackendRegistry.with_defaults()
        backend = await registry.create_backend("real-esrgan", config, retry, cb)
    """

    def __init__(self) -> None:
        """Initialise an empty backend registry."""
        self._builders: dict[str, UpscaleBackendBuilder] = {}

    @classmethod
    def with_defaults(cls) -> UpscaleBackendRegistry:
        """Return a registry populated with the built-in upscale backends."""
        registry = cls()

        async def _real_esrgan(
            config: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kw: Any,
        ) -> Any:
            from lexigram.multimedia.upscale.providers.real_esrgan import (
                RealEsrganUpscaleProvider,
            )

            return RealEsrganUpscaleProvider(
                base_url=config.real_esrgan_base_url,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        async def _hat(
            config: Any,
            retry: Any,
            circuit_breaker: Any,
            **_kw: Any,
        ) -> Any:
            from lexigram.multimedia.upscale.providers.hat import HatUpscaleProvider

            return HatUpscaleProvider(
                base_url=config.hat_base_url,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        registry.register("real-esrgan", _real_esrgan)
        registry.register("hat", _hat)
        return registry

    def register(self, backend: str, builder: UpscaleBackendBuilder) -> None:
        """Register a builder under a backend name."""
        self._builders[backend] = builder

    async def create_backend(
        self,
        backend: str,
        config: Any,
        retry: Any,
        circuit_breaker: Any,
    ) -> Any:
        """Build an upscale provider for a backend name."""
        builder = self._builders.get(backend)
        if builder is None:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented upscale backend: {backend!r}"
            )
        return await builder(config, retry, circuit_breaker)

    def backends(self) -> list[str]:
        """Return the registered backend names."""
        return list(self._builders.keys())

    def __contains__(self, backend: str) -> bool:
        return backend in self._builders


__all__ = ["UpscaleBackendBuilder", "UpscaleBackendRegistry"]
