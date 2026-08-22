"""Write-side repository for the event-driven orders demo."""

from __future__ import annotations

from orders.domain import Order
from orders.identifier import new_order_id


class OrderRepository:
    """In-memory store for the write-side order aggregate state."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def next_id(self) -> str:
        """Return the next order identifier."""
        return new_order_id()

    def save(self, order: Order) -> None:
        """Persist an order state."""
        self._orders[order.order_id] = order

    def get(self, order_id: str) -> Order | None:
        """Return the order with the given id, if present."""
        return self._orders.get(order_id)

    def list_all(self) -> list[Order]:
        """Return all orders, newest first."""
        return list(reversed(list(self._orders.values())))


__all__ = ["OrderRepository"]
