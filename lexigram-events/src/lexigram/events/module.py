"""Events (CQRS / event-sourcing) module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.events import (
    CommandBusProtocol,
    EventBusProtocol,
    QueryBusProtocol,
)
from lexigram.di.module import DynamicModule, Module, module


@module(is_global=True)
class EventsModule(Module):
    """CQRS + Event Sourcing: CommandBusProtocol, QueryBusProtocol, EventBusProtocol, EventStoreProtocol, sagas.

    Call :meth:`configure` to configure the events subsystem.

    Usage::

        from lexigram.events.config import EventsConfig
        from lexigram.events.types import EventStoreBackend

        @module(
            imports=[
                EventsModule.configure(
                    EventsConfig(event_store_backend=EventStoreBackend.MEMORY)
                )
            ]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(
        cls,
        config: Any | None = None,
        handler_modules: list[str] | None = None,
    ) -> DynamicModule:
        """Create an EventsModule with explicit configuration.

        Args:
            config: :class:`~lexigram.events.config.EventsConfig` or ``None``
                for framework defaults (in-memory event store).
            handler_modules: Python module paths to auto-discover event/command
                handlers from (e.g. ``["myapp.handlers"]``).

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.events.admin.contributor import EventsAdminContributor
        from lexigram.events.admin.handlers.dead_letter_count import (
            DeadLetterCountWidgetHandler,
        )
        from lexigram.events.admin.handlers.events_throughput import (
            EventsThroughputWidgetHandler,
        )
        from lexigram.events.di.provider import EventsProvider

        return DynamicModule(
            module=cls,
            providers=[EventsProvider(config=config, handler_modules=handler_modules)],
            exports=[
                EventBusProtocol,
                CommandBusProtocol,
                QueryBusProtocol,
                EventsAdminContributor,
                EventsThroughputWidgetHandler,
                DeadLetterCountWidgetHandler,
            ],
        )

    @classmethod
    def scope(cls, *handlers: type, **kwargs: Any) -> DynamicModule:
        """Scope event/command/query handler classes into a feature module.

        Registers the given handler classes as providers so they are resolved
        by the bus implementations.  The parent module graph must already
        include :meth:`EventsModule.configure` — this does **not** create a
        new event store or bus.

        Uses the anonymous token pattern so both ``configure()`` and
        ``scope()`` can coexist in the same compiled graph without a
        ``ModuleDuplicateError``.

        Example::

            @module(
                imports=[
                    EventsModule.configure(config),
                    EventsModule.scope(
                        CreateOrderHandler,
                        GetOrderHandler,
                        OrderShippedHandler,
                    ),
                ]
            )
            class OrderFeatureModule(Module):
                pass

        Args:
            *handlers: Command, query, or event handler classes to register.

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
            providers=list(handlers),
            exports=[],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return an in-memory EventsModule for unit testing.

        Registers an in-memory event store with no external broker
        connections. Suitable for testing event handlers and CQRS logic.

        Returns:
            A DynamicModule backed by in-memory event storage.
        """
        from lexigram.events.di.provider import EventsProvider

        return DynamicModule(
            module=cls,
            providers=[EventsProvider()],
            exports=[EventBusProtocol, CommandBusProtocol, QueryBusProtocol],
        )


__all__ = ["EventsModule"]
