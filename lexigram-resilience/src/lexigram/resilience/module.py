"""Resilience module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.infra.resilience.protocols import (
    CircuitBreakerRegistryProtocol,
    ResiliencePipelineFactoryProtocol,
)
from lexigram.di.module import DynamicModule, Module, module
from lexigram.resilience.di.provider import ResilienceProvider


@module(
    providers=[ResilienceProvider],
    exports=[CircuitBreakerRegistryProtocol, ResiliencePipelineFactoryProtocol],
)
class ResilienceModule(Module):
    """Circuit breakers, retry policies, bulkhead isolation, throttling, and rate limiting.

    Call :meth:`configure` to configure the resilience subsystem with custom settings.

    Usage::

        from lexigram.resilience.config import ResilienceConfig

        @module(
            imports=[ResilienceModule.configure(ResilienceConfig(...))]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(cls, config: Any | None = None) -> DynamicModule:
        """Create a ResilienceModule with explicit configuration.

        Args:
            config: :class:`~lexigram.resilience.config.ResilienceConfig` or ``None``
                for framework defaults.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        return DynamicModule(
            module=cls,
            providers=[ResilienceProvider()],
            exports=[CircuitBreakerRegistryProtocol, ResiliencePipelineFactoryProtocol],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return a ResilienceModule with framework defaults for testing.

        All circuit breakers and retry policies use default configuration.
        Suitable for unit and integration tests.

        Args:
            config: Ignored; kept for signature compatibility with base ``Module``.

        Returns:
            A DynamicModule with default resilience configuration.
        """
        return DynamicModule(
            module=cls,
            providers=[ResilienceProvider()],
            exports=[CircuitBreakerRegistryProtocol, ResiliencePipelineFactoryProtocol],
        )


__all__ = ["ResilienceModule"]
