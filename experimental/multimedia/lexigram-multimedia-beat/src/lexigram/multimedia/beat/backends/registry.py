"""Beat analysis backend registry — registry-based dispatch of beat backends."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError

BeatBackendBuilder = Callable[..., Awaitable[Any]]


class BeatBackendRegistry:
    """Registry of beat-analysis-backend builders, keyed by backend name.

    Usage::

        registry = BeatBackendRegistry.with_defaults()
        backend = await registry.create_backend("librosa", config, retry, cb)
    """

    def __init__(self) -> None:
        """Initialise an empty backend registry."""
        self._builders: dict[str, BeatBackendBuilder] = {}

    @classmethod
    def with_defaults(cls) -> BeatBackendRegistry:
        """Return a registry populated with the built-in beat backends."""
        registry = cls()

        async def _librosa(
            config: Any, retry: Any, circuit_breaker: Any, **_kw: Any,
        ) -> Any:
            from lexigram.multimedia.beat.providers.librosa import (
                LibrosaBeatAnalysisProvider,
            )

            return LibrosaBeatAnalysisProvider(
                sample_rate=config.librosa_sample_rate,
                max_asset_bytes=config.max_asset_bytes,
                max_analyze_samples=config.max_analyze_samples,
            )

        async def _madmom(
            config: Any, retry: Any, circuit_breaker: Any, **_kw: Any,
        ) -> Any:
            from lexigram.multimedia.beat.providers.madmom import (
                MadmomBeatAnalysisProvider,
            )

            return MadmomBeatAnalysisProvider(
                base_url=config.madmom_base_url,
                timeout=config.timeout,
                retry=retry,
                circuit_breaker=circuit_breaker,
            )

        registry.register("librosa", _librosa)
        registry.register("madmom", _madmom)
        return registry

    def register(self, backend: str, builder: BeatBackendBuilder) -> None:
        """Register a builder under a backend name."""
        self._builders[backend] = builder

    async def create_backend(
        self, backend: str, config: Any, retry: Any, circuit_breaker: Any,
    ) -> Any:
        """Build a beat analysis provider for a backend name."""
        builder = self._builders.get(backend)
        if builder is None:
            raise ProviderNotInstalledError(
                f"Unknown or unimplemented beat-analysis backend: {backend!r}"
            )
        return await builder(config, retry, circuit_breaker)

    def backends(self) -> list[str]:
        """Return the registered backend names."""
        return list(self._builders.keys())

    def __contains__(self, backend: str) -> bool:
        return backend in self._builders


__all__ = ["BeatBackendBuilder", "BeatBackendRegistry"]
