"""REST endpoint tests for the event-driven orders demo.

Boots ``OrdersModule`` (events + web wiring) through the real container,
resolves ``OrdersApiController``, and drives its routes via an
``httpx.AsyncClient`` over a minimal Starlette app — mirroring how
``main.py serve`` mounts them.
"""

from __future__ import annotations

from typing import AsyncIterator

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route

from lexigram.app import Application
from lexigram.web import JSONResponse

from orders.controllers.api import OrdersApiController
from orders.module import OrdersModule


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with Application.boot(
        name="orders-api-test", modules=[OrdersModule.configure()]
    ) as app:
        controller = await app.container.resolve(OrdersApiController)

        def json(
            handler,
        ):  # wrap controller methods into plain Starlette endpoints
            async def endpoint(request: Request) -> JSONResponse:
                result = await handler(request)
                if isinstance(result, JSONResponse):
                    return result
                return JSONResponse(result)

            return endpoint

        asgi = Starlette(
            routes=[
                Route("/orders", json(controller.place_order), methods=["POST"]),
                Route("/orders", json(controller.list_orders), methods=["GET"]),
                Route(
                    "/orders/{order_id}",
                    json(controller.get_order),
                    methods=["GET"],
                ),
                Route(
                    "/orders/{order_id}/pay",
                    json(controller.pay_order),
                    methods=["POST"],
                ),
                Route(
                    "/orders/{order_id}/ship",
                    json(controller.ship_order),
                    methods=["POST"],
                ),
                Route("/outbox", json(controller.list_outbox), methods=["GET"]),
                Route(
                    "/outbox/flush",
                    json(controller.flush_outbox),
                    methods=["POST"],
                ),
            ]
        )
        transport = httpx.ASGITransport(app=asgi)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as http:
            yield http


def _place_payload(customer: str = "Alice") -> dict[str, object]:
    return {
        "customer": customer,
        "items": [{"sku": "SKU-1", "qty": 2, "unit_price": "9.99"}],
    }


async def test_place_pay_ship_over_http(client: httpx.AsyncClient) -> None:
    placed = await client.post("/orders", json=_place_payload())
    assert placed.status_code == 201
    order_id = placed.json()["order_id"]
    assert placed.json()["status"] == "placed"

    paid = await client.post(f"/orders/{order_id}/pay", json={"amount": "19.98"})
    assert paid.status_code == 200

    shipped = await client.post(f"/orders/{order_id}/ship")
    assert shipped.status_code == 200

    # Read-side projections advance when the transactional outbox flushes.
    await client.post("/outbox/flush")

    row = (await client.get(f"/orders/{order_id}")).json()
    assert row["status"] == "shipped"


async def test_ship_unpaid_maps_to_409(client: httpx.AsyncClient) -> None:
    order_id = (
        await client.post("/orders", json=_place_payload("Bob"))
    ).json()["order_id"]

    response = await client.post(f"/orders/{order_id}/ship")

    assert response.status_code == 409
    assert "paid" in response.json()["error"].lower()


async def test_unknown_order_maps_to_404(client: httpx.AsyncClient) -> None:
    missing = await client.get("/orders/nope")
    assert missing.status_code == 404

    shipped = await client.post("/orders/nope/ship")
    assert shipped.status_code == 404


async def test_place_validates_payload(client: httpx.AsyncClient) -> None:
    no_items = await client.post("/orders", json={"customer": "C"})
    assert no_items.status_code == 400

    bad_item = await client.post(
        "/orders",
        json={"customer": "C", "items": [{"qty": "x"}]},
    )
    assert bad_item.status_code == 400

    no_customer = await client.post("/orders", json={"items": []})
    assert no_customer.status_code == 400


async def test_list_and_get_read_model(client: httpx.AsyncClient) -> None:
    order_id = (await client.post("/orders", json=_place_payload())).json()[
        "order_id"
    ]
    await client.post("/outbox/flush")  # publish staged events to the read side

    rows = (await client.get("/orders")).json()
    assert any(row["order_id"] == order_id for row in rows)


async def test_outbox_inspection_and_flush(client: httpx.AsyncClient) -> None:
    order_id = (await client.post("/orders", json=_place_payload())).json()[
        "order_id"
    ]
    await client.post(f"/orders/{order_id}/pay", json={"amount": "19.98"})

    staged = (await client.get("/outbox")).json()
    assert isinstance(staged, list) and staged

    flushed = (await client.post("/outbox/flush")).json()
    assert flushed["ok"] is True
    assert flushed["flushed"] >= len(staged)
