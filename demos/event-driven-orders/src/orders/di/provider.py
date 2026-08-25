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
from lexigram.contracts.core.health import (
    HealthCheckResult,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.contracts.events import CommandBusProtocol, EventBusProtocol
from lexigram.di.provider import Provider
from orders.commands import PayOrder, PlaceOrder, ShipOrder
from orders.domain import OrderPaid, OrderPlaced, OrderShipped
from orders.events import NotificationHandler, OrdersView
from orders.handlers import PayOrderHandler, PlaceOrderHandler, ShipOrderHandler
from orders.repository.order_repository import OrderRepository
from orders.repository.outbox import Outbox
from orders.services.orders_api import OrdersApi


class OrdersProvider(Provider):
    """Provide the order write/read sides and their bus wiring."""

    name = "orders"
    priority = ProviderPriority.NORMAL

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(OrderRepository, OrderRepository)
        container.singleton(OrdersView, OrdersView)
        container.singleton(NotificationHandler, NotificationHandler)
        container.singleton(Outbox, Outbox)
        # The facade needs buses wired in boot(); build lazily.
        container.singleton(OrdersApi, factory=self._build_api)

    async def _build_api(self, resolver: ContainerResolverProtocol) -> OrdersApi:
        """Register handlers/subscriptions, then assemble the facade."""
        repository = await resolver.resolve(OrderRepository)
        outbox = await resolver.resolve(Outbox)
        command_bus = await resolver.resolve(CommandBusProtocol)
        command_bus.register(
            PlaceOrder,
            PlaceOrderHandler(repository=repository, outbox=outbox),
        )
        command_bus.register(
            PayOrder,
            PayOrderHandler(repository=repository, outbox=outbox),
        )
        command_bus.register(
            ShipOrder,
            ShipOrderHandler(repository=repository, outbox=outbox),
        )
        event_bus = await resolver.resolve(EventBusProtocol)
        view = await resolver.resolve(OrdersView)
        notifier = await resolver.resolve(NotificationHandler)
        event_bus.subscribe(OrderPlaced, view.on_order_placed)
        event_bus.subscribe(OrderPaid, view.on_order_paid)
        event_bus.subscribe(OrderShipped, view.on_order_shipped)
        event_bus.subscribe(OrderPlaced, notifier.on_order_placed)
        event_bus.subscribe(OrderShipped, notifier.on_order_shipped)
        return OrdersApi(
            command_bus=command_bus,
            event_bus=event_bus,
            repository=repository,
            view=view,
            outbox=outbox,
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Wire handlers/subscriptions eagerly, before the app serves.

        Resolving ``OrdersApi`` triggers ``_build_api`` exactly once
        (singleton), reproducing the original boot-time wiring contract:
        any consumer may dispatch or publish straight after start().
        """
        self._api = await container.resolve(OrdersApi)

    async def shutdown(self) -> None:
        """Nothing to tear down; the demo is fully in-memory."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report write/read-side readiness with outbox depth."""
        return HealthCheckResult(
            component=self.name,
            details={
                "wired": getattr(self, "_api", None) is not None,
                "outbox_depth": (
                    len(self._api.list_outbox()) if getattr(self, "_api", None) else 0
                ),
            },
        )


__all__ = ["OrdersProvider"]
