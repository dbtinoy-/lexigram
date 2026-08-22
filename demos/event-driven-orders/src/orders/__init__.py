"""Event-driven orders demo application package."""

from __future__ import annotations

from orders.commands import PayOrder, PlaceOrder, ShipOrder
from orders.domain import (
    Order,
    OrderError,
    OrderItem,
    OrderPaid,
    OrderPlaced,
    OrderShipped,
    OrderStatus,
)
from orders.events import NotificationHandler, OrdersView, OrderView
from orders.module import OrdersModule
from orders.repository.order_repository import OrderRepository
from orders.repository.outbox import Outbox, OutboxRecord, OutboxStatus
from orders.services.orders_api import OrdersApi

__all__ = [
    "NotificationHandler",
    "Order",
    "OrderError",
    "OrderItem",
    "OrderPaid",
    "OrderPlaced",
    "OrderRepository",
    "OrderShipped",
    "OrderStatus",
    "OrderView",
    "OrdersApi",
    "OrdersModule",
    "OrdersView",
    "Outbox",
    "OutboxRecord",
    "OutboxStatus",
    "PayOrder",
    "PlaceOrder",
    "ShipOrder",
]
