"""Entry point for the event-driven orders demo (CQRS).

Usage::

    uv run python -m orders place "Alice Wonder" --item "SKU-1,2,9.99" --item "SKU-2,1,149.00"
    uv run python -m orders pay <order-id> 9.99
    uv run python -m orders ship <order-id>
    uv run python -m orders list
    uv run python -m orders outbox
    uv run python -m orders demo
    uv run python -m orders serve        # REST API on :7074 (ORDERS_PORT to override)
"""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal
import os
import sys

from lexigram.app import Application
from orders.domain import OrderItem
from orders.module import OrdersModule
from orders.services import OrdersApi


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orders", description="Event-driven orders demo (CQRS)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_place = sub.add_parser("place", help="place a new order")
    p_place.add_argument("customer")
    p_place.add_argument(
        "--item", action="append", default=[], help="sku,qty,unit_price"
    )

    p_pay = sub.add_parser("pay", help="mark an order paid")
    p_pay.add_argument("order_id")
    p_pay.add_argument("amount", type=Decimal)

    p_ship = sub.add_parser("ship", help="mark an order shipped")
    p_ship.add_argument("order_id")

    sub.add_parser("list", help="list projected orders")
    sub.add_parser("outbox", help="show and flush the outbox")
    sub.add_parser("demo", help="run the full lifecycle in one process")
    p_serve = sub.add_parser("serve", help="serve the REST API (default :7074)")
    p_serve.add_argument("--port", type=int, default=None)
    return parser


def _parse_item(spec: str) -> OrderItem:
    parts = spec.split(",")
    if len(parts) != 3:
        raise SystemExit(f"invalid --item '{spec}'; expected sku,qty,unit_price")
    sku, qty, price = parts
    return OrderItem(sku=sku, name=sku, qty=int(qty), unit_price=Decimal(price))


async def _serve(port: int) -> None:
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    async with Application.boot(
        name="orders", modules=[OrdersModule.configure(port=port)]
    ) as app:
        await app.container.resolve(OrdersApi)  # wire buses/handlers eagerly
        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


async def _run(args: argparse.Namespace) -> None:
    if args.command == "serve":
        port = args.port or int(os.environ.get("ORDERS_PORT", "7074"))
        await _serve(port)
        return
    async with Application.boot(
        name="orders", modules=[OrdersModule.configure()]
    ) as app:
        api = await app.container.resolve(OrdersApi)

        if args.command == "place":
            items = [_parse_item(spec) for spec in args.item]
            order_id = await api.place(args.customer, items)
            print(f"order placed: {order_id}")
        elif args.command == "pay":
            await api.pay(args.order_id, args.amount)
            print(f"order paid: {args.order_id} ({args.amount})")
        elif args.command == "ship":
            await api.ship(args.order_id)
            print(f"order shipped: {args.order_id}")
        elif args.command == "list":
            for row in api.list_orders():
                print(
                    f"{row['order_id']}\t{row['customer']}\t{row['total']}\t{row['status']}"
                )
        elif args.command == "outbox":
            for record in api.list_outbox():
                print(f"{record['event_type']}\t{record['status']}")
            sent = await api.flush_outbox()
            print(f"flushed: {sent}")
        elif args.command == "demo":
            items = [_parse_item("SKU-1,2,9.99"), _parse_item("SKU-2,1,149.00")]
            order_id = await api.place("Alice Wonder", items)
            print(f"order placed: {order_id}")
            await api.pay(order_id, Decimal("168.98"))
            print(f"order paid: {order_id} (168.98)")
            await api.ship(order_id)
            print(f"order shipped: {order_id}")
            for record in api.list_outbox():
                print(f"{record['event_type']}\t{record['status']}")
            sent = await api.flush_outbox()
            await api.event_bus.flush()
            for row in api.list_orders():
                print(
                    f"{row['order_id']}\t{row['customer']}\t{row['total']}\t{row['status']}"
                )
            print(f"flushed: {sent}")


def main() -> None:
    args = _build_parser().parse_args()
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
