"""Relay module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.relay.protocols import (
    RelayConverterProtocol,
    RelayRegistryProtocol,
)
from lexigram.di.module import DynamicModule, Module, module

__all__ = ["RelayModule"]


@module
class RelayModule(Module):
    """Relay protocol conversion engine module for Lexigram applications.

    Provides the caller-owned relay registry and the public conversion
    engine behind their contract protocols.

    Usage::

        from lexigram.ai.relay import RelayModule

        @module(
            imports=[RelayModule.configure()]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(cls) -> DynamicModule:
        """Create a RelayModule with the built-in converter routes.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.relay.di.provider import RelayProvider

        return DynamicModule(
            module=cls,
            providers=[RelayProvider()],
            exports=[
                RelayConverterProtocol,
                RelayRegistryProtocol,
            ],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Create a RelayModule suitable for unit and integration testing.

        Uses the same in-memory registry and synchronous engine as
        :meth:`configure`; no credentials or I/O are involved.

        Args:
            config: Optional test configuration override; the relay module
                needs no configuration, so it is ignored.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.relay.di.provider import RelayProvider

        return DynamicModule(
            module=cls,
            providers=[RelayProvider()],
            exports=[
                RelayConverterProtocol,
                RelayRegistryProtocol,
            ],
        )
