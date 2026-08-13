"""Events (CQRS) demo module.

Imports the framework's events module (in-memory buses + store) and the
orders feature module that wires the write and read sides onto those buses.
"""

from __future__ import annotations

from lexigram.contracts.events import EventBusProtocol
from lexigram.di.module import DynamicModule, Module, module
from lexigram.events.module import EventsModule
from orders.commands import PayOrder, PlaceOrder, ShipOrder
from orders.di.provider import OrdersProvider
from orders.events import NotificationHandler, OrdersView
from orders.outbox import Outbox
from orders.repositories import OrderRepository


@module()
class OrdersModule(Module):
    """Root module for the event-driven orders demo."""

    @classmethod
    def configure(cls) -> DynamicModule:
        return DynamicModule(
            module=cls,
            imports=[EventsModule.configure()],
            providers=[OrdersProvider],
            exports=[
                EventBusProtocol,
                OrderRepository,
                OrdersView,
                NotificationHandler,
                Outbox,
                PlaceOrder,
                PayOrder,
                ShipOrder,
            ],
        )


__all__ = ["OrdersModule"]
