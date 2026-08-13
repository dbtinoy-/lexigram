"""QueueModule — IoC module for lexigram-queue."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.queue.config import QueueConfig


@module(is_global=True)
class QueueModule(Module):
    """Message queue/bus integration with Named DI multi-backend support.

    Registers :class:`~lexigram.contracts.queue.protocols.QueueProtocol` for
    constructor injection.

    Usage::

        from lexigram.queue.config import QueueConfig, NamedQueueConfig
        from lexigram.queue.module import QueueModule

        @module(
            imports=[QueueModule.configure(QueueConfig(backends=[...]))]
        )
        class AppModule(Module):
            pass

    Scope consumers into a feature module::

        @module(
            imports=[
                QueueModule.configure(QueueConfig(...)),
                QueueModule.scope(OrderConsumer, PaymentConsumer),
            ]
        )
        class OrdersFeatureModule(Module):
            pass

    Named injection::

        class MyService:
            def __init__(
                self,
                queue: QueueProtocol,                                   # primary
                events: Annotated[QueueProtocol, Named("events")],     # named
            ) -> None: ...
    """

    @classmethod
    def configure(cls, config: QueueConfig | Any | None = None) -> DynamicModule:
        """Create a QueueModule with explicit configuration.

        Args:
            config: :class:`~lexigram.queue.config.QueueConfig` or ``None``
                to use defaults (reads from environment variables).

        Returns:
            A :class:`~lexigram.queue.module.DynamicModule` descriptor.
        """
        from lexigram.queue.admin.contributor import QueueAdminContributor
        from lexigram.queue.admin.handlers.consumer_lag import ConsumerLagWidgetHandler
        from lexigram.queue.admin.handlers.failed_messages import (
            FailedMessagesWidgetHandler,
        )
        from lexigram.queue.admin.handlers.queue_depth import QueueDepthWidgetHandler
        from lexigram.queue.di.provider import QueueProvider

        return DynamicModule(
            module=cls,
            providers=[QueueProvider(config=config)],
            exports=[
                QueueProtocol,
                QueueAdminContributor,
                QueueDepthWidgetHandler,
                ConsumerLagWidgetHandler,
                FailedMessagesWidgetHandler,
            ],
            is_global=True,
        )

    @classmethod
    def scope(cls, *consumers: type, **kwargs: Any) -> DynamicModule:
        """Scope queue consumer classes into a feature module.

        Registers the given consumer classes as providers so they are
        discovered and wired by the queue backend.  The parent module graph
        must already include :meth:`QueueModule.configure` — this does
        **not** create a new queue connection.

        Uses the anonymous token pattern so both ``configure()`` and
        ``scope()`` can coexist in the same compiled graph without a
        ``ModuleDuplicateError``.

        Example::

            @module(
                imports=[
                    QueueModule.configure(QueueConfig(...)),
                    QueueModule.scope(OrderConsumer, PaymentConsumer),
                ]
            )
            class OrdersFeatureModule(Module):
                pass

        Args:
            *consumers: Queue consumer classes to register.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` scoped to this feature.
        """
        token = type(
            f"_{cls.__name__}Scope",
            (cls,),
            {"__lexigram_scope_of__": cls},
        )
        return DynamicModule(
            module=token,
            providers=list(consumers),
            exports=[],
        )

    @classmethod
    def stub(cls, config: QueueConfig | None = None) -> DynamicModule:
        """Return an in-memory QueueModule for unit testing.

        Uses a memory backend so no external broker is required.

        Args:
            config: Optional config override; defaults to empty QueueConfig
                (which uses memory backend).

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.queue.config import NamedQueueConfig, QueueConfig
        from lexigram.queue.di.provider import QueueProvider

        config = config or QueueConfig(
            backends=[NamedQueueConfig(name="default", driver="memory")]
        )
        return DynamicModule(
            module=cls,
            providers=[QueueProvider(config=config)],
            exports=[QueueProtocol],
        )


__all__ = ["QueueModule"]
