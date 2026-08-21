"""Tests for the event-driven orders demo.

Boots the whole module (framework events subsystem + orders wiring) via the
application container, then drives the write side through the command bus and
verifies the read side has been projected from the published events.
"""

from __future__ import annotations

from decimal import Decimal
from typing import AsyncIterator

import pytest

from lexigram.app import Application
from lexigram.contracts.events import EventBusProtocol
from lexigram.contracts.exceptions import EventError
from lexigram.events.buses.command import CommandBusImpl
from lexigram.result import Err, Result

from orders.commands import PayOrder, PlaceOrder, ShipOrder
from orders.domain import OrderItem, OrderNotPaidError, OrderPlaced, OrderStatus
from orders.events import NotificationHandler, OrdersView
from orders.main import _build_parser, _run
from orders.module import OrdersModule
from orders.outbox import Outbox, OutboxError
from orders.repositories import OrderRepository
from orders.services import OrdersApi


@pytest.fixture
async def app() -> AsyncIterator[Application]:
    async with Application.boot(
        name="orders-test", modules=[OrdersModule.configure()]
    ) as instance:
        yield instance


def item(sku: str, qty: int = 1, price: str = "10.00") -> OrderItem:
    return OrderItem(sku=sku, name=sku, qty=qty, unit_price=Decimal(price))


class TestOrderLifecycle:
    async def test_place_pay_ship_projects_events(self, app: Application) -> None:
        command_bus = await app.container.resolve(CommandBusImpl)
        event_bus = await app.container.resolve(EventBusProtocol)
        outbox = await app.container.resolve(Outbox)
        view = await app.container.resolve(OrdersView)

        order_id = await command_bus.dispatch(
            PlaceOrder(customer="Alice Wonder", items=[item("SKU-1", 2, "9.99")])
        )
        await command_bus.dispatch(PayOrder(order_id=order_id, amount=Decimal("19.98")))
        await command_bus.dispatch(ShipOrder(order_id=order_id))

        # Delivery happens only through the outbox relay: flush publishes the
        # staged events, then the bus drain runs the subscribed handlers.
        staged = await outbox.flush(event_bus)
        assert staged.is_ok()
        assert staged.unwrap() == 3
        await event_bus.flush()

        row = view.get(order_id)
        assert row is not None
        assert row.total == Decimal("19.98")
        assert row.status is OrderStatus.SHIPPED
        assert row.timeline == ["placed", "paid", "shipped"]

    async def test_read_model_has_no_write_access(self, app: Application) -> None:
        command_bus = await app.container.resolve(CommandBusImpl)
        event_bus = await app.container.resolve(EventBusProtocol)
        outbox = await app.container.resolve(Outbox)
        view = await app.container.resolve(OrdersView)

        order_id = await command_bus.dispatch(
            PlaceOrder(customer="Bob", items=[item("SKU-2")])
        )
        await outbox.flush(event_bus)
        await event_bus.flush()

        row = view.get(order_id)
        assert row is not None
        assert row.customer == "Bob"

        # The read model only knows what events told it: shipping before paying
        # is rejected by the write side, so the read model stays on 'placed'.
        with pytest.raises(Exception):
            await command_bus.dispatch(ShipOrder(order_id=order_id))
        assert view.get(order_id).status is OrderStatus.PLACED

    async def test_every_write_is_staged_in_outbox(self, app: Application) -> None:
        command_bus = await app.container.resolve(CommandBusImpl)
        outbox = await app.container.resolve(Outbox)

        order_id = await command_bus.dispatch(
            PlaceOrder(customer="Carol", items=[item("SKU-3")])
        )
        await command_bus.dispatch(PayOrder(order_id=order_id, amount=Decimal("10.00")))

        event_types = [record.event_type for record in outbox.all()]
        assert event_types == ["OrderPlaced", "OrderPaid"]

    async def test_dispatch_rejects_invalid_transition(self, app: Application) -> None:
        command_bus = await app.container.resolve(CommandBusImpl)
        order_id = await command_bus.dispatch(
            PlaceOrder(customer="Dan", items=[item("SKU-4")])
        )

        with pytest.raises(OrderNotPaidError) as exc_info:
            await command_bus.dispatch(ShipOrder(order_id=order_id))
        assert "paid before shipping" in str(exc_info.value)

    async def test_orders_api_resolves_from_container(self, app: Application) -> None:
        api = await app.container.resolve(OrdersApi)
        event_bus = await app.container.resolve(EventBusProtocol)

        order_id = await api.place("Bob Belcher", [item("SKU-9", 1, "12.00")])
        await api.pay(order_id, Decimal("12.00"))
        await api.flush_outbox()
        await event_bus.flush()

        rows = api.list_orders()
        assert rows[0]["order_id"] == order_id
        assert rows[0]["status"] == "paid"


class TestOutbox:
    async def test_flush_delivers_pending_events(self, app: Application) -> None:
        command_bus = await app.container.resolve(CommandBusImpl)
        event_bus = await app.container.resolve(EventBusProtocol)
        outbox = await app.container.resolve(Outbox)

        order_id = await command_bus.dispatch(
            PlaceOrder(customer="Eve", items=[item("SKU-5")])
        )

        assert outbox.pending()
        result = await outbox.flush(event_bus)
        assert result.is_ok()
        assert result.unwrap() == 1
        assert not outbox.pending()


class TestDemoCommand:
    async def test_demo_runs_full_lifecycle_in_one_process(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        args = _build_parser().parse_args(["demo"])
        await _run(args)

        out = capsys.readouterr().out
        assert "order placed:" in out
        assert "order paid:" in out
        assert "order shipped:" in out
        assert "\tshipped" in out
        assert "flushed: 3" in out


class TestOutboxFailurePaths:
    async def test_flush_returns_err_and_preserves_pending_when_bus_rejects(
        self, app: Application
    ) -> None:
        command_bus = await app.container.resolve(CommandBusImpl)
        outbox = await app.container.resolve(Outbox)
        event_bus = await app.container.resolve(EventBusProtocol)

        await command_bus.dispatch(PlaceOrder(customer="Frank", items=[item("SKU-6")]))
        assert len(outbox.pending()) == 1

        class RejectingBus:
            async def publish(self, event: object) -> Result[None, EventError]:
                return Err(EventError("bus rejected"))

        result = await outbox.flush(RejectingBus())
        assert result.is_err()
        assert "Failed to publish OrderPlaced" in str(result.unwrap_err())
        # The failed record stays pending so a later relay can retry it.
        assert len(outbox.pending()) == 1

        retry = await outbox.flush(event_bus)
        assert retry.is_ok()
        assert retry.unwrap() == 1
        assert not outbox.pending()

    def test_stage_raises_when_outbox_is_full(self) -> None:
        outbox = Outbox(max_records=1)
        outbox.stage(OrderPlaced(order_id="o-1"))

        with pytest.raises(OutboxError):
            outbox.stage(OrderPlaced(order_id="o-2"))


class TestNotifications:
    async def test_notifications_record_side_effects(self, app: Application) -> None:
        api = await app.container.resolve(OrdersApi)
        event_bus = await app.container.resolve(EventBusProtocol)
        notifier = await app.container.resolve(NotificationHandler)

        order_id = await api.place("Grace Hopper", [item("SKU-7")])
        await api.pay(order_id, Decimal("10.00"))
        await api.ship(order_id)
        await api.flush_outbox()
        await event_bus.flush()

        assert notifier.notifications == [
            f"order {order_id}: confirmation email sent to Grace Hopper",
            f"order {order_id}: tracking email sent",
        ]
