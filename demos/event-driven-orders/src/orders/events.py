"""Read model and notification handlers for the event-driven orders demo.

These live on the **read side**: they consume published domain events and
project them into a query-friendly view. They never dispatch commands — the
write side stays authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from lexigram.logging import get_logger
from orders.domain import OrderPaid, OrderPlaced, OrderShipped, OrderStatus

logger = get_logger(__name__)


@dataclass
class OrderView:
    """One row of the query-side order view.

    Attributes:
        order_id: Order identifier.
        customer: Customer name.
        total: Order total.
        status: Latest status known to the read model.
        timeline: Collected events, newest first.
    """

    order_id: str
    customer: str = ""
    total: Decimal = Decimal("0")
    status: OrderStatus = OrderStatus.PLACED
    timeline: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""
        return {
            "order_id": self.order_id,
            "customer": self.customer,
            "total": str(self.total),
            "status": self.status.value,
            "timeline": list(reversed(self.timeline)),
        }


class OrdersView:
    """Read-side projection of order state, fed exclusively by events."""

    def __init__(self) -> None:
        self._rows: dict[str, OrderView] = {}

    async def on_order_placed(self, event: OrderPlaced) -> None:
        """Project an ``OrderPlaced`` event into the view."""
        row = self._rows.setdefault(
            event.order_id,
            OrderView(order_id=event.order_id),
        )
        row.customer = event.customer
        row.total = event.total
        row.status = OrderStatus.PLACED
        row.timeline.append("placed")

    async def on_order_paid(self, event: OrderPaid) -> None:
        """Project an ``OrderPaid`` event into the view."""
        row = self._rows.setdefault(
            event.order_id,
            OrderView(order_id=event.order_id),
        )
        row.status = OrderStatus.PAID
        row.timeline.append("paid")

    async def on_order_shipped(self, event: OrderShipped) -> None:
        """Project an ``OrderShipped`` event into the view."""
        row = self._rows.setdefault(
            event.order_id,
            OrderView(order_id=event.order_id),
        )
        row.status = OrderStatus.SHIPPED
        row.timeline.append("shipped")

    def get(self, order_id: str) -> OrderView | None:
        """Return the projected row for an order, if any."""
        return self._rows.get(order_id)

    def list_all(self) -> list[OrderView]:
        """Return all projected rows, newest first."""
        return list(reversed(list(self._rows.values())))


class NotificationHandler:
    """Side-effect handler: notify the customer about order events."""

    def __init__(self) -> None:
        self.notifications: list[str] = []

    async def on_order_placed(self, event: OrderPlaced) -> None:
        """Append a notification for a placed order."""
        message = f"order {event.order_id}: confirmation email sent to {event.customer}"
        self.notifications.append(message)
        logger.info("notification_sent", message=message)

    async def on_order_shipped(self, event: OrderShipped) -> None:
        """Append a notification for a shipped order."""
        message = f"order {event.order_id}: tracking email sent"
        self.notifications.append(message)
        logger.info("notification_sent", message=message)


__all__ = ["NotificationHandler", "OrderView", "OrdersView"]
