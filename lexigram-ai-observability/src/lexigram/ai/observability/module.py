"""Observability module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.observability.ai import AITracerProtocol
from lexigram.di.module import DynamicModule, Module, module


@module()
class ObservabilityModule(Module):
    """AI Observability module — registers ObservabilityProvider."""

    @classmethod
    def configure(cls, config: Any | None = None) -> DynamicModule:
        """Create an ObservabilityModule with explicit configuration."""
        return DynamicModule(
            module=cls,
            providers=[cls._resolve_provider(config)],
            exports=[AITracerProtocol],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return a no-op ObservabilityModule for testing.

        Honors *config* identically to :meth:`configure`; the provider
        registers no-op tracers and metrics when the features are disabled.

        Args:
            config: Optional config override; dicts are coerced.

        Returns:
            A DynamicModule with noop observability configuration.
        """
        return cls.configure(config=config)

    @staticmethod
    def _resolve_provider(config: Any) -> Any:
        """Resolve the observability provider honoring typed and dict configs.

        Args:
            config: ``None``, an ``ObservabilityConfig``, or a plain dict
                of the same keys.

        Returns:
            The configured provider instance.

        Raises:
            TypeError: When *config* is neither ``None``, a dict, nor an
                ``ObservabilityConfig``.
        """
        from lexigram.ai.observability.config import ObservabilityConfig
        from lexigram.ai.observability.di.provider import ObservabilityProvider

        if config is None:
            return ObservabilityProvider()
        if isinstance(config, dict):
            return ObservabilityProvider(config=ObservabilityConfig(**config))
        if isinstance(config, ObservabilityConfig):
            return ObservabilityProvider(config=config)
        raise TypeError(
            f"config must be ObservabilityConfig or dict, got {type(config).__name__}"
        )


__all__ = ["ObservabilityModule"]
