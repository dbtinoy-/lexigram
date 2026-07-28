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
        from lexigram.ai.observability.config import ObservabilityConfig
        from lexigram.ai.observability.di.provider import ObservabilityProvider

        if config is not None:
            if isinstance(config, dict):
                provider = ObservabilityProvider(config=ObservabilityConfig(**config))
            elif isinstance(config, ObservabilityConfig):
                provider = ObservabilityProvider(config=config)
            else:
                raise TypeError(
                    f"config must be ObservabilityConfig or dict, got {type(config).__name__}"
                )
        else:
            provider = ObservabilityProvider()

        return DynamicModule(
            module=cls,
            providers=[provider],
            exports=[AITracerProtocol],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return a no-op ObservabilityModule for testing.

        Registers observability infrastructure with noop tracing and metrics.
        No external telemetry systems are connected.

        Returns:
            A DynamicModule with noop observability configuration.
        """
        from lexigram.ai.observability.di.provider import ObservabilityProvider

        return DynamicModule(
            module=cls,
            providers=[ObservabilityProvider()],
            exports=[AITracerProtocol],
        )


__all__ = ["ObservabilityModule"]
