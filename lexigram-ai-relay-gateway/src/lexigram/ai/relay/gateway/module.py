"""Relay gateway module for dependency injection."""

from __future__ import annotations

from lexigram.contracts.ai.relay import RelayGatewayProtocol
from lexigram.di.module import DynamicModule, Module, module

__all__ = ["RelayGatewayModule"]


@module
class RelayGatewayModule(Module):
    """Protocol-facing relay gateway module for Lexigram applications.

    Provides the relay gateway behind the :class:`RelayGatewayProtocol`
    contract: channel selection, orchestration, upstream I/O, and SSE
    handling.  The :class:`RelayGatewayProvider` composes the gateway
    from caller-owned config, conversion engine, and HTTP client.

    Usage::

        from lexigram.ai.relay.gateway import RelayGatewayModule

        @module(
            imports=[RelayGatewayModule.configure()]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(cls) -> DynamicModule:
        """Create a RelayGatewayModule with the built-in gateway routes.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.relay.gateway.di.provider import RelayGatewayProvider
        from lexigram.ai.relay.gateway.operations.controls import RelayControlsService
        from lexigram.ai.relay.gateway.operations.health import RelayHealthService
        from lexigram.ai.relay.gateway.operations.metrics import RelayMetricsService

        return DynamicModule(
            module=cls,
            providers=[RelayGatewayProvider()],
            exports=[
                RelayGatewayProtocol,
                RelayHealthService,
                RelayMetricsService,
                RelayControlsService,
            ],
        )
