"""REST surface for the event-driven orders demo.

Maps the ``OrdersApi`` facade onto HTTP so the CQRS lifecycle can be driven
from a browser or curl alongside the existing CLI:

- ``POST /orders``                       — place an order
- ``GET /orders`` / ``GET /orders/{id}`` — read-model queries
- ``POST /orders/{id}/pay|ship``         — lifecycle commands
- ``GET /outbox`` / ``POST /outbox/flush`` — transactional outbox inspection

Lifecycle handlers return the facade's ``Result`` directly; the pipeline
renders ``Ok`` payloads and maps domain errors to ProblemDetail responses
using the registered mappings below (unknown order → 404, state conflicts
→ 409, other order errors → 400).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from starlette.requests import Request

from lexigram.result import Err, Result
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, JSONResponse, get, post
from lexigram.web.routing.result_bridge import ResultResponseMapper
from orders.domain import (
    OrderAlreadyPaidError,
    OrderAlreadyShippedError,
    OrderError,
    OrderItem,
    OrderNotFoundError,
    OrderNotPaidError,
)
from orders.services.orders_api import OrdersApi

# Domain error → HTTP status mappings (rendered as ProblemDetail bodies).
# Base first: register() inserts at front, so leaves must be registered
# AFTER the base to take precedence.
ResultResponseMapper.register(OrderError, 400)
ResultResponseMapper.register(OrderNotPaidError, 409)
ResultResponseMapper.register(OrderAlreadyPaidError, 409)
ResultResponseMapper.register(OrderAlreadyShippedError, 409)
ResultResponseMapper.register(OrderNotFoundError, 404)


class OrdersApiController(Controller):
    """Expose the order write/read sides over HTTP."""

    def __init__(self, api: OrdersApi) -> None:
        self.api = api

    @post("/orders")
    async def place_order(self, request: Request) -> JSONResponse:
        """Place a new order from a JSON customer/items payload."""
        body = json_loads(await request.body())
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

    @post("/orders/{order_id}/pay")
    async def pay_order(
        self,
        request: Request,
    ) -> Result[None, OrderError]:
        """Mark an order paid."""
        order_id = request.path_params["order_id"]
        body = json_loads(await request.body())
        try:
            amount = Decimal(str(body.get("amount", "0")))
        except InvalidOperation:
            return Err(OrderError("invalid amount"))
        try:
            return await self.api.pay(order_id=order_id, amount=amount)
        except OrderError as exc:
            return Err(exc)

    @post("/orders/{order_id}/ship")
    async def ship_order(self, request: Request) -> Result[None, OrderError]:
        """Mark an order shipped (requires the order to be paid)."""
        order_id = request.path_params["order_id"]
        try:
            return await self.api.ship(order_id)
        except OrderError as exc:
            return Err(exc)

    @get("/outbox")
    async def list_outbox(self, request: Request | None = None) -> list[dict[str, Any]]:
        """Return staged outbox records in order."""
        return self.api.list_outbox()

    @post("/outbox/flush")
    async def flush_outbox(
        self, request: Request | None = None
    ) -> Result[dict, Exception]:
        """Flush staged events through the event bus."""
        flushed = await self.api.flush_outbox()
        return flushed.map_sync(lambda count: {"ok": True, "flushed": count})


__all__ = ["OrdersApiController"]
