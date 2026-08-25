"""Interactive teaching CLI for the event-driven orders demo.

Public surface: :func:`build_parser` and :func:`main`. Every command boots the
real application via ``orders.app.create_app`` and narrates the CQRS
lifecycle through the command bus → events → read model.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal

from lexigram.logging import get_logger
from orders.app import create_app
from orders.domain import OrderItem
from orders.services.orders_api import OrdersApi

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the ``orders`` command-line parser."""
    parser = argparse.ArgumentParser(
        prog="orders", description="Event-driven orders demo (CQRS)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    place = sub.add_parser("place", help="place a new order")
    place.add_argument("customer")
    place.add_argument("--item", action="append", default=[], help="sku,qty,unit_price")

    pay = sub.add_parser("pay", help="mark an order paid")
    pay.add_argument("order_id")
    pay.add_argument("amount", type=Decimal)

    ship = sub.add_parser("ship", help="mark an order shipped")
    ship.add_argument("order_id")

    sub.add_parser("list", help="list projected orders")
    sub.add_parser("outbox", help="show and flush the outbox")
    sub.add_parser("demo", help="run the full lifecycle in one process")
    return parser


def parse_item(spec: str) -> OrderItem:
    """Parse ``sku,qty,unit_price`` into an :class:`OrderItem`."""
    parts = spec.split(",")
    if len(parts) != 3:
        raise SystemExit(f"invalid --item '{spec}'; expected sku,qty,unit_price")
    sku, qty, price = parts
    return OrderItem(sku=sku, name=sku, qty=int(qty), unit_price=Decimal(price))


async def place(api: OrdersApi, customer: str, items: list[OrderItem]) -> str | None:
    """Place an order; returns the order id or ``None`` when rejected."""
    placed = await api.place(customer, items)
    if placed.is_err():
        logger.error("order.rejected", reason=str(placed.unwrap_err()))
        return None
    order_id = placed.unwrap()
    logger.info("order.placed", order_id=order_id)
    return order_id


async def pay(api: OrdersApi, order_id: str, amount: Decimal) -> int:
    paid = await api.pay(order_id, amount)
    if paid.is_err():
        logger.error("order.rejected", reason=str(paid.unwrap_err()))
        return 1
    logger.info("order.paid", order_id=order_id, amount=str(amount))
    return 0


async def ship(api: OrdersApi, order_id: str) -> int:
    shipped = await api.ship(order_id)
    if shipped.is_err():
        logger.error("order.rejected", reason=str(shipped.unwrap_err()))
        return 1
    logger.info("order.shipped", order_id=order_id)
    return 0


async def list_orders(api: OrdersApi) -> None:
    for row in api.list_orders():
        logger.info(
            "order.row",
            order_id=row["order_id"],
            customer=row["customer"],
            total=str(row["total"]),
            status=row["status"],
        )


async def outbox(api: OrdersApi) -> int:
    for record in api.list_outbox():
        logger.info(
            "outbox.record",
            event_type=record["event_type"],
            status=record["status"],
        )
    flushed = await api.flush_outbox()
    if flushed.is_err():
        logger.error("outbox.flush_failed", error=str(flushed.unwrap_err()))
        return 1
    logger.info("outbox.flushed", count=flushed.unwrap())
    return 0


async def five_step_demo(api: OrdersApi) -> int:
    """Place → pay → ship → inspect outbox → read model, in one process."""
    items = [parse_item("SKU-1,2,9.99"), parse_item("SKU-2,1,149.00")]
    order_id = await place(api, "Alice Wonder", items)
    if order_id is None:
        return 1

    if (await pay(api, order_id, Decimal("168.98"))) != 0:
        return 1
    if (await ship(api, order_id)) != 0:
        return 1
    return await outbox(api)


async def run(args: argparse.Namespace) -> int:
    """Dispatch the parsed command against one booted application."""
    app = create_app()
    try:
        await app.start()
        await app.container.resolve(OrdersApi)  # wire buses/handlers eagerly
        api = await app.container.resolve(OrdersApi)

        async def do_place() -> int:
            order_id = await place(
                api, args.customer, [parse_item(spec) for spec in args.item]
            )
            return 1 if order_id is None else 0

        async def do_pay() -> int:
            return await pay(api, args.order_id, args.amount)

        async def do_ship() -> int:
            return await ship(api, args.order_id)

        commands: dict[str, Callable[[], Awaitable[object]]] = {
            "place": do_place,
            "list": lambda: list_orders(api),
            "pay": do_pay,
            "ship": do_ship,
            "outbox": lambda: outbox(api),
            "demo": lambda: five_step_demo(api),
        }
        outcome = await commands[args.command]()
        return int(outcome) if isinstance(outcome, int) else 0
    finally:
        await app.stop()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    args = build_parser().parse_args(argv)
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


__all__ = ["build_parser", "main"]
