"""Query-side service facade for the event-driven orders demo.

Resolves the framework buses and demo services once, then exposes simple
methods the CLI (or a future web controller) can call.
"""

from __future__ import annotations

from decimal import Decimal

from lexigram.contracts.events import EventBusProtocol
from lexigram.events.buses.command import CommandBusImpl
from orders.commands import PayOrder, PlaceOrder, ShipOrder
from orders.domain import OrderItem
from orders.events import OrdersView
from orders.outbox import Outbox
from orders.repositories import OrderRepository


class OrdersApi:
    """Facade over the command bus, read model and outbox.

    Args:
        command_bus: The command bus.
        event_bus: The event bus.
        repository: The write-side repository.
        view: The read-side projection.
        outbox: The staged-event outbox.
    """

    def __init__(
        self,
        command_bus: CommandBusImpl,
        event_bus: EventBusProtocol,
        repository: OrderRepository,
        view: OrdersView,
        outbox: Outbox,
    ) -> None:
        self.command_bus = command_bus
        self.event_bus = event_bus
        self.repository = repository
        self.view = view
        self.outbox = outbox

    async def place(self, customer: str, items: list[OrderItem]) -> str:
        """Dispatch ``PlaceOrder`` and return the new order id."""
        return await self.command_bus.dispatch(
            PlaceOrder(customer=customer, items=items)
        )

    async def pay(self, order_id: str, amount: Decimal) -> None:
        """Dispatch ``PayOrder``."""
        await self.command_bus.dispatch(PayOrder(order_id=order_id, amount=amount))

    async def ship(self, order_id: str) -> None:
        """Dispatch ``ShipOrder``."""
        await self.command_bus.dispatch(ShipOrder(order_id=order_id))

    def list_orders(self) -> list[dict[str, object]]:
        """Return the read-model rows for every order."""
        return [row.to_dict() for row in self.view.list_all()]

    def list_outbox(self) -> list[dict[str, object]]:
        """Return outbox records in staging order."""
        return [
            {
                "event_type": record.event_type,
                "status": record.status.value,
            }
            for record in self.outbox.all()
        ]

    async def flush_outbox(self) -> int:
        """Flush staged events through the event bus; return count sent."""
        result = await self.outbox.flush(self.event_bus)
        if result.is_err():
            raise result.unwrap_err()
        return result.unwrap()


__all__ = ["OrdersApi"]
