"""Lexigram Idempotency Module.

Provides the idempotency subsystem as a self-contained Lexigram Module,
registering the in-memory IdempotencyStoreProtocol implementation.
"""

from __future__ import annotations

from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol
from lexigram.di.module import DynamicModule, Module, module
from lexigram.resilience.config import IdempotencyConfig
from lexigram.resilience.idempotency.provider import IdempotencyProvider


@module()
class IdempotencyModule(Module):
    """Self-contained module that wires up the idempotency store.

    Usage::

        app = App(modules=[IdempotencyModule.configure()])

    Or with a custom config::

        app = App(modules=[IdempotencyModule.configure(IdempotencyConfig(ttl=300))])
    """

    @classmethod
    def configure(cls, config: IdempotencyConfig | None = None) -> DynamicModule:
        """Build a DynamicModule for the idempotency subsystem.

        Args:
            config: Optional idempotency configuration. When ``None`` the
                provider uses its defaults.

        Returns:
            A DynamicModule that registers IdempotencyProvider and exports
            IdempotencyStoreProtocol.

        Raises:
            TypeError: When *config* is not ``None`` and not an IdempotencyConfig.
        """
        if config is not None and not isinstance(config, IdempotencyConfig):
            raise TypeError(
                f"config must be IdempotencyConfig, got {type(config).__name__}"
            )
        return DynamicModule(
            module=cls,
            providers=[IdempotencyProvider(config=config)],
            exports=[IdempotencyStoreProtocol],
        )


__all__ = ["IdempotencyModule"]
