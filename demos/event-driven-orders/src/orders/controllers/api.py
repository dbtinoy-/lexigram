"""REST surface for the event-driven orders demo.

Maps the ``OrdersApi`` facade onto HTTP so the CQRS lifecycle can be driven
from a browser or curl alongside the existing CLI:

- ``POST /orders``                       — place an order
- ``GET /orders`` / ``GET /orders/{id}`` — read-model queries
- ``POST /orders/{id}/pay|ship``         — lifecycle commands
- ``GET /outbox`` / ``POST /outbox/flush`` — transactional outbox inspection

The controller registers the demo's own error vocabulary with the Result
bridge via ``@error_status``, so lifecycle handlers surface facade errors
as-is: unknown order → 404, state conflicts → 409, remaining ``OrderError``
subclasses → 400 through the ``DomainError`` fallback. No handler re-expresses
a domain error as a contracts base class just to pick an HTTP status.

Payload parsing for ``place_order``/``pay`` is intentionally explicit rather
than DTO-bound: prices and amounts are ``Decimal`` values, and the request
binder does not coerce strings to ``Decimal`` (only to simple scalars), so
the demo converts money at the boundary itself.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from starlette.requests import Request

from lexigram.contracts.exceptions.domain import ValidationError
from lexigram.result import Err, Ok, Result
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, get, post
from lexigram.web.routing.result_bridge import error_status
from orders.domain import (
    OrderAlreadyPaidError,
    OrderAlreadyShippedError,
    OrderError,
    OrderItem,
    OrderNotFoundError,
    OrderNotPaidError,
)
from orders.services.orders_api import OrdersApi


@error_status(OrderNotFoundError, 404)
@error_status(OrderNotPaidError, 409)
@error_status(OrderAlreadyPaidError, 409)
@error_status(OrderAlreadyShippedError, 409)
class OrdersApiController(Controller):
    """Expose the order write/read sides over HTTP."""

    def __init__(self, api: OrdersApi) -> None:
        self.api = api

    @post("/orders", status_code=201)
    async def place_order(
        self,
        request: Request,
    ) -> Result[dict, ValidationError | OrderError]:
        """Place a new order from a JSON customer/items payload."""
        body = json_loads(await request.body())
        customer = str(body.get("customer") or "").strip()
        if not customer:
            return Err(ValidationError("customer is required"))

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
                return Err(ValidationError(f"invalid item: {exc}"))
        if not parsed:
            return Err(ValidationError("at least one item is required"))

        placed = await self.api.place(customer=customer, items=parsed)
        if placed.is_err():
            return Err(placed.unwrap_err())
        order_id = placed.unwrap()
        return Ok({"order_id": order_id, "status": "placed"})

    @get("/orders")
    async def list_orders(self) -> list[dict]:
        """Return the projected read-model rows."""
        return self.api.list_orders()

    @get("/orders/{order_id}")
    async def get_order(
        self,
        order_id: str,
    ) -> Result[dict, OrderNotFoundError]:
        """Return one projected order row."""
        for row in self.api.list_orders():
            if row.get("order_id") == order_id:
                return Ok(row)
        return Err(OrderNotFoundError(f"unknown order {order_id}"))

    @post("/orders/{order_id}/pay")
    async def pay_order(
        self,
        order_id: str,
        request: Request,
    ) -> Result[dict, OrderError]:
        """Mark an order paid."""
        body = json_loads(await request.body())
        try:
            amount = Decimal(str(body.get("amount", "0")))
        except InvalidOperation:
            return Err(OrderError("invalid amount"))
        # The facade surfaces write-side rejections by raising; the
        # boundary translates them into ``Err`` so the Result bridge —
        # with the ``@error_status`` mappings above — renders them.
        try:
            paid = await self.api.pay(order_id=order_id, amount=amount)
        except OrderError as exc:
            return Err(exc)
        if paid.is_err():
            return Err(paid.unwrap_err())
        return Ok({"ok": True})

    @post("/orders/{order_id}/ship")
    async def ship_order(
        self,
        order_id: str,
    ) -> Result[dict, OrderError]:
        """Mark an order shipped (requires the order to be paid)."""
        try:
            shipped = await self.api.ship(order_id)
        except OrderError as exc:
            return Err(exc)
        if shipped.is_err():
            return Err(shipped.unwrap_err())
        return Ok({"ok": True})

    @get("/outbox")
    async def list_outbox(self) -> list[dict]:
        """Return staged outbox records in order."""
        return self.api.list_outbox()

    @post("/outbox/flush")
    async def flush_outbox(self) -> Result[dict, Exception]:
        """Flush staged events through the event bus."""
        flushed = await self.api.flush_outbox()
        return flushed.map_sync(lambda count: {"ok": True, "flushed": count})


__all__ = ["OrdersApiController"]
