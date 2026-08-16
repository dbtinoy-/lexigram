"""Serialization module for dependency injection."""

from __future__ import annotations

from lexigram.contracts.core.serialization import (
    JsonSerializerProtocol,
    SerializerProtocol,
)
from lexigram.di.module import DynamicModule, Module, module


@module()
class SerializationModule(Module):
    """JSON serialization and schema utilities for the Lexigram Framework.

    Call :meth:`configure` to register a configured
    :class:`~lexigram.serialization.di.provider.SerializationProvider` and expose
    :class:`~lexigram.contracts.core.serialization.JsonSerializerProtocol` for injection.

    Usage::

        from lexigram.serialization import SerializationModule

        @module(
            imports=[SerializationModule.configure()]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(cls, config: object | None = None) -> DynamicModule:
        """Create a SerializationModule with explicit configuration.

        Args:
            config: :class:`~lexigram.serialization.config.SerializationConfig` or
                ``None`` for framework defaults.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.serialization.di.provider import SerializationProvider

        if config is not None:
            from lexigram.serialization.config import SerializationConfig

            if not isinstance(config, SerializationConfig):
                raise TypeError(
                    f"config must be SerializationConfig, got {type(config).__name__}"
                )

        provider = SerializationProvider(config=config)

        return DynamicModule(
            module=cls,
            providers=[provider],
            exports=[JsonSerializerProtocol, SerializerProtocol],
        )


__all__ = ["SerializationModule"]
