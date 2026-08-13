"""Concurrency module for dependency injection."""

from __future__ import annotations

from lexigram.contracts.core import DispatcherProtocol, TaskManagerProtocol
from lexigram.di.module import DynamicModule, Module, module


@module()
class ConcurrencyModule(Module):
    """Async dispatcher and task manager for the Lexigram Framework.

    Call :meth:`configure` to register a configured
    :class:`~lexigram.concurrency.di.provider.ConcurrencyProvider` and expose
    :class:`~lexigram.contracts.core.DispatcherProtocol` and
    :class:`~lexigram.contracts.core.TaskManagerProtocol` for injection.

    Usage::

        from lexigram.concurrency import ConcurrencyModule, ConcurrencyConfig

        @module(
            imports=[ConcurrencyModule.configure(ConcurrencyConfig(...))]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(cls, config: object | None = None) -> DynamicModule:
        """Create a ConcurrencyModule with explicit configuration.

        Args:
            config: :class:`~lexigram.concurrency.config.ConcurrencyConfig` or
                ``None`` for framework defaults.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.concurrency.di.provider import ConcurrencyProvider

        provider = ConcurrencyProvider()
        if config is not None:
            from lexigram.concurrency.config import ConcurrencyConfig

            if not isinstance(config, ConcurrencyConfig):
                raise TypeError(
                    f"config must be ConcurrencyConfig, got {type(config).__name__}"
                )
            provider._config = config  # noqa: SLF001

        return DynamicModule(
            module=cls,
            providers=[provider],
            exports=[DispatcherProtocol, TaskManagerProtocol],
        )


__all__ = ["ConcurrencyModule"]
