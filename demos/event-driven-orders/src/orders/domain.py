"""Value types and domain errors for the event-driven orders demo.

Shows the CQRS hands-off: **commands** are intents handled by the command bus
(write side); every state change is announced as a **domain event** that read
models, notifications and triggers subscribe to (read side).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from lexigram.contracts.domain import DomainEvent
from lexigram.contracts.exceptions.domain import DomainError


class OrderStatus(str, Enum):
    """Lifecycle of an order as seen by the write side."""

    PLACED = "placed"
    PAID = "paid"
    SHIPPED = "shipped"


class OrderError(DomainError):
    """Base error for order domain operations."""


class OrderNotPaidError(OrderError):
    """Raised when shipping is attempted before the order is paid."""


class OrderAlreadyPaidError(OrderError):
    """Raised when an order is paid twice."""


class OrderAlreadyShippedError(OrderError):
    """Raised when an order is shipped twice."""


class OrderNotFoundError(OrderError):
    """Raised when an order id does not match any known order."""


@dataclass(frozen=True)
class OrderItem:
    """A single line on an order.

    Attributes:
        sku: Stock-keeping unit identifier.
        name: Display name.
        qty: Quantity ordered.
        unit_price: Unit price; stored as ``Decimal`` to avoid float drift.
    """

    sku: str
    name: str
    qty: int
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        """Return the line total."""
        return self.unit_price * self.qty


@dataclass(frozen=True)
class Order:
    """Aggregate state for one order (the write-side state).

    Attributes:
        order_id: Unique order identifier.
        customer: Customer name.
        total: Order total.
        status: Current status.
    """

    order_id: str
    customer: str
    total: Decimal
    status: OrderStatus = OrderStatus.PLACED


class OrderPlaced(DomainEvent):
    """Announced when ``PlaceOrder`` succeeds."""

    order_id: str = ""
    customer: str = ""
    total: Decimal = Decimal("0")


class OrderPaid(DomainEvent):
    """Announced when ``PayOrder`` succeeds."""

    order_id: str = ""
    amount: Decimal = Decimal("0")


class OrderShipped(DomainEvent):
    """Announced when ``ShipOrder`` succeeds."""

    order_id: str = ""


def order_event(
    event_cls: type[DomainEvent],
    order_id: str,
    aggregate_id: UUID | None = None,
    **payload: Any,
) -> DomainEvent:
    """Build a domain event with aggregate context attached.

    Args:
        event_cls: The event class to instantiate.
        order_id: Order identifier (also attached as aggregate_id).
        aggregate_id: Optional override for the aggregate id.
        **payload: Event-specific fields.

    Returns:
        An :class:`DomainEvent` instance ready for the event bus.
    """
    return event_cls(
        aggregate_id=aggregate_id or UUID(order_id),
        aggregate_type="order",
        event_type=event_cls.__name__,
        order_id=order_id,
        **payload,
    )


__all__ = [
    "Order",
    "OrderAlreadyPaidError",
    "OrderAlreadyShippedError",
    "OrderError",
    "OrderItem",
    "OrderNotFoundError",
    "OrderNotPaidError",
    "OrderPaid",
    "OrderPlaced",
    "OrderShipped",
    "OrderStatus",
    "order_event",
]
