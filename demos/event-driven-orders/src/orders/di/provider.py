"""Provider for the event-driven orders demo.

Wires the write side (repository, command handlers, outbox) and read side
(projection, notifications) onto the framework-provided command and event
buses. All handlers are constructor-injected services; no service locator.
"""

from __future__ import annotations

from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.contracts.events import EventBusProtocol
from lexigram.di.provider import Provider
from lexigram.events.buses.command import CommandBusImpl
from orders.commands import PayOrder, PlaceOrder, ShipOrder
from orders.domain import OrderPaid, OrderPlaced, OrderShipped
from orders.events import NotificationHandler, OrdersView
from orders.handlers import PayOrderHandler, PlaceOrderHandler, ShipOrderHandler
from orders.outbox import Outbox
from orders.repositories import OrderRepository
from orders.services import OrdersApi


class OrdersProvider(Provider):
    """Provide the order write/read sides and their bus wiring."""

    name = "orders"
    priority = ProviderPriority.NORMAL

    def __init__(self) -> None:
        super().__init__()
        self._api: OrdersApi | None = None

    def _get_api(self) -> OrdersApi:
        """Return the API facade assembled during boot."""
        if self._api is None:
            raise RuntimeError("OrdersProvider has not been booted yet")
        return self._api

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(OrderRepository, OrderRepository())
        container.singleton(OrdersView, OrdersView())
        container.singleton(NotificationHandler, NotificationHandler())
        container.singleton(Outbox, Outbox())
        # The facade depends on buses that are only wired in boot(), so it is
        # registered as a lazy factory here and assembled once boot completes.
        container.singleton(OrdersApi, factory=self._get_api)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        repository = await container.resolve(OrderRepository)
        event_bus = await container.resolve(EventBusProtocol)
        outbox = await container.resolve(Outbox)
        view = await container.resolve(OrdersView)
        notifier = await container.resolve(NotificationHandler)

        command_bus = await container.resolve(CommandBusImpl)
        command_bus.register(
            PlaceOrder,
            PlaceOrderHandler(
                repository=repository, event_bus=event_bus, outbox=outbox
            ),
        )
        command_bus.register(
            PayOrder,
            PayOrderHandler(repository=repository, event_bus=event_bus, outbox=outbox),
        )
        command_bus.register(
            ShipOrder,
            ShipOrderHandler(repository=repository, event_bus=event_bus, outbox=outbox),
        )

        event_bus.subscribe(OrderPlaced, view.on_order_placed)
        event_bus.subscribe(OrderPaid, view.on_order_paid)
        event_bus.subscribe(OrderShipped, view.on_order_shipped)
        event_bus.subscribe(OrderPlaced, notifier.on_order_placed)
        event_bus.subscribe(OrderShipped, notifier.on_order_shipped)

        self._api = OrdersApi(
            command_bus=command_bus,
            event_bus=event_bus,
            repository=repository,
            view=view,
            outbox=outbox,
        )

    async def shutdown(self) -> None:
        """Nothing to tear down; the demo is fully in-memory."""


__all__ = ["OrdersProvider"]
