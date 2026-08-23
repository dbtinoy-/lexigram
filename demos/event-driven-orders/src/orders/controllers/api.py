"""REST surface for the event-driven orders demo.

Maps the ``OrdersApi`` facade onto HTTP so the CQRS lifecycle can be driven
from a browser or curl alongside the existing CLI:

- ``POST /orders``                       — place an order
- ``GET /orders`` / ``GET /orders/{id}`` — read-model queries
- ``POST /orders/{id}/pay|ship``         — lifecycle commands
- ``GET /outbox`` / ``POST /outbox/flush`` — transactional outbox inspection

Lifecycle handlers return the facade's ``Result`` directly; the pipeline
renders ``Ok`` payloads and maps domain errors to ProblemDetail responses
via their contracts base classes (validation → 422, state conflicts → 409,
unknown order → 404).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from starlette.requests import Request

from lexigram.contracts.exceptions.domain import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from lexigram.result import Err, Ok, Result
from lexigram.serialization import loads as json_loads
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


class OrdersApiController(Controller):
    """Expose the order write/read sides over HTTP."""

    def __init__(self, api: OrdersApi) -> None:
        self.api = api

    @post("/orders", status_code=201)
    async def place_order(
        self,
        request: Request,
    ) -> Result[dict, ValidationError]:
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
    async def list_orders(self, request: Request | None = None) -> list[dict]:
        """Return the projected read-model rows."""
        return self.api.list_orders()

    @get("/orders/{order_id}")
    async def get_order(
        self,
        request: Request,
    ) -> Result[dict, NotFoundError]:
        """Return one projected order row."""
        order_id = request.path_params["order_id"]
        for row in self.api.list_orders():
            if row.get("order_id") == order_id:
                return Ok(row)
        return Err(NotFoundError(f"unknown order {order_id}"))

    @post("/orders/{order_id}/pay")
    async def pay_order(
        self,
        request: Request,
    ) -> Result[dict, OrderError | ConflictError | NotFoundError]:
        """Mark an order paid."""
        order_id = request.path_params["order_id"]
        body = json_loads(await request.body())
        try:
            amount = Decimal(str(body.get("amount", "0")))
        except InvalidOperation:
            return Err(OrderError("invalid amount"))
        try:
            paid = await self.api.pay(order_id=order_id, amount=amount)
        except OrderError as exc:
            return Err(_conflict_or_not_found(exc))
        if paid.is_err():
            return Err(_conflict_or_not_found(paid.unwrap_err()))
        return Ok({"ok": True})

    @post("/orders/{order_id}/ship")
    async def ship_order(
        self,
        request: Request,
    ) -> Result[dict, OrderError | ConflictError | NotFoundError]:
        """Mark an order shipped (requires the order to be paid)."""
        order_id = request.path_params["order_id"]
        try:
            shipped = await self.api.ship(order_id)
        except OrderError as exc:
            return Err(_conflict_or_not_found(exc))
        if shipped.is_err():
            return Err(_conflict_or_not_found(shipped.unwrap_err()))
        return Ok({"ok": True})

    @get("/outbox")
    async def list_outbox(self, request: Request | None = None) -> list[dict]:
        """Return staged outbox records in order."""
        return self.api.list_outbox()

    @post("/outbox/flush")
    async def flush_outbox(
        self, request: Request | None = None
    ) -> Result[dict, Exception]:
        """Flush staged events through the event bus."""
        flushed = await self.api.flush_outbox()
        return flushed.map_sync(lambda count: {"ok": True, "flushed": count})


def _conflict_or_not_found(err: OrderError) -> OrderError:
    """Re-express facade errors as their semantic contracts base classes."""
    if isinstance(err, OrderNotFoundError):
        return NotFoundError(str(err))
    if isinstance(
        err, (OrderNotPaidError, OrderAlreadyPaidError, OrderAlreadyShippedError)
    ):
        return ConflictError(str(err))
    return err


__all__ = ["OrdersApiController"]
