"""Events (CQRS) demo module.

Imports the framework's events module (in-memory buses + store) and the
orders feature module that wires the write and read sides onto those buses.
"""

from __future__ import annotations

import os

from lexigram.contracts.events import EventBusProtocol
from lexigram.di.module import DynamicModule, Module, module
from lexigram.events.module import EventsModule
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig
from orders.api import OrdersApiController
from orders.commands import PayOrder, PlaceOrder, ShipOrder
from orders.di.provider import OrdersProvider
from orders.events import NotificationHandler, OrdersView
from orders.outbox import Outbox
from orders.repositories import OrderRepository
from orders.services import OrdersApi


@module()
class OrdersModule(Module):
    """Root module for the event-driven orders demo."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = (
            port if port is not None else int(os.environ.get("ORDERS_PORT", "7074"))
        )
        return DynamicModule(
            module=cls,
            imports=[
                EventsModule.configure(),
                WebModule.configure(
                    controllers=[OrdersApiController],
                    web_config=WebConfig(
                        server=ServerConfig(host="127.0.0.1", port=selected_port),
                        # The API is meant for curl/external tools, not a
                        # browser form flow — disable CSRF like realtime-monitor.
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[OrdersProvider],
            exports=[
                EventBusProtocol,
                OrdersApi,
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
