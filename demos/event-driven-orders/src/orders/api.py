"""REST surface for the event-driven orders demo.

Maps the ``OrdersApi`` facade onto HTTP so the CQRS lifecycle can be driven
from a browser or curl alongside the existing CLI:

- ``POST /orders``                       — place an order
- ``GET /orders`` / ``GET /orders/{id}`` — read-model queries
- ``POST /orders/{id}/pay|ship``         — lifecycle commands
- ``GET /outbox`` / ``POST /outbox/flush`` — transactional outbox inspection

Domain failures map to status codes: unknown order → 404, state conflicts
(``OrderNotPaidError`` / already-paid / already-shipped) → 409.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from decimal import Decimal, InvalidOperation
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.contracts.exceptions.events import HandlerNotFoundError
from lexigram.web import Controller, get, post
from orders.domain import (
    OrderAlreadyPaidError,
    OrderAlreadyShippedError,
    OrderError,
    OrderItem,
    OrderNotFoundError,
    OrderNotPaidError,
)
from orders.services.orders_api import OrdersApi

_CONFLICTS = (
    OrderNotPaidError,
    OrderAlreadyPaidError,
    OrderAlreadyShippedError,
)


class OrdersApiController(Controller):
    """Expose the order write/read sides over HTTP."""

    def __init__(self, api: OrdersApi) -> None:
        self.api = api

    @post("/orders")
    async def place_order(self, request: Request) -> JSONResponse:
        """Place a new order from a JSON customer/items payload."""
        body = await request.json()
        customer = str(body.get("customer") or "").strip()
        if not customer:
            return JSONResponse({"error": "customer is required"}, status_code=400)

        parsed: list[OrderItem] = []
        for raw in body.get("items") or []:
            try:
                sku = str(raw["sku"])
                parsed.append(
                    OrderItem(
                        sku=sku,
                        name=sku,
                        qty=int(raw.get("qty", 1)),
                        unit_price=Decimal(str(raw.get("unit_price", "0"))),
                    )
                )
            except (KeyError, InvalidOperation, ValueError, TypeError) as exc:
                return JSONResponse({"error": f"invalid item: {exc}"}, status_code=400)
        if not parsed:
            return JSONResponse(
                {"error": "at least one item is required"}, status_code=400
            )

        placed = await self.api.place(customer=customer, items=parsed)
        if placed.is_err():
            return JSONResponse({"error": str(placed.unwrap_err())}, status_code=409)
        order_id = placed.unwrap()
        return JSONResponse({"order_id": order_id, "status": "placed"}, status_code=201)

    @get("/orders")
    async def list_orders(self, request: Request | None = None) -> list[dict[str, Any]]:
        """Return the projected read-model rows."""
        return self.api.list_orders()

    @get("/orders/{order_id}")
    async def get_order(self, request: Request) -> JSONResponse:
        """Return one projected order row."""
        order_id = request.path_params["order_id"]
        for row in self.api.list_orders():
            if row.get("order_id") == order_id:
                return JSONResponse(row)
        return JSONResponse({"error": f"unknown order {order_id}"}, status_code=404)

    async def _dispatch(
        self, run: Callable[[], Coroutine[Any, Any, None]]
    ) -> JSONResponse:
        """Run a lifecycle command, mapping domain failures to statuses."""
        try:
            await run()
        except OrderNotFoundError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        except _CONFLICTS as exc:
            return JSONResponse({"error": str(exc)}, status_code=409)
        except (HandlerNotFoundError, OrderError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse({"ok": True})

    @post("/orders/{order_id}/pay")
    async def pay_order(self, request: Request) -> JSONResponse:
        """Mark an order paid."""
        order_id = request.path_params["order_id"]
        body = await request.json()
        try:
            amount = Decimal(str(body.get("amount", "0")))
        except InvalidOperation:
            return JSONResponse({"error": "invalid amount"}, status_code=400)
        return await self._dispatch(
            lambda: self.api.pay(order_id=order_id, amount=amount)
        )

    @post("/orders/{order_id}/ship")
    async def ship_order(self, request: Request) -> JSONResponse:
        """Mark an order shipped (requires the order to be paid)."""
        order_id = request.path_params["order_id"]
        return await self._dispatch(lambda: self.api.ship(order_id))

    @get("/outbox")
    async def list_outbox(self, request: Request | None = None) -> list[dict[str, Any]]:
        """Return staged outbox records in order."""
        return self.api.list_outbox()

    @post("/outbox/flush")
    async def flush_outbox(self, request: Request | None = None) -> JSONResponse:
        """Flush staged events through the event bus."""
        flushed = await self.api.flush_outbox()
        if flushed.is_err():
            return JSONResponse({"error": str(flushed.unwrap_err())}, status_code=502)
        return JSONResponse({"ok": True, "flushed": flushed.unwrap()})


__all__ = ["OrdersApiController"]
