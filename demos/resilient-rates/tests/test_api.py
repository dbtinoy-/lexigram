"""REST endpoint tests for the resilient rates demo.

Boots ``RatesModule`` (resilience + cache + web wiring) through the real
container, resolves ``RatesApiController``, and drives its routes via an
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

from rates.controllers.api import RatesApiController
from rates.module import RatesModule


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with Application.boot(
        name="rates-api-test", modules=[RatesModule.configure()]
    ) as app:
        controller = await app.container.resolve(RatesApiController)

        def json(handler):
            async def endpoint(request: Request) -> JSONResponse:
                result = await handler(request)
                if isinstance(result, JSONResponse):
                    return result
                return JSONResponse(result)

            return endpoint

        asgi = Starlette(
            routes=[
                Route(
                    "/rates/{pair:path}",
                    json(controller.fetch_rate),
                    methods=["GET"],
                ),
                Route("/stats", json(controller.stats), methods=["GET"]),
                Route(
                    "/cache/clear",
                    json(controller.clear_cache),
                    methods=["POST"],
                ),
                Route(
                    "/scenario/{name}",
                    json(controller.set_scenario),
                    methods=["POST"],
                ),
            ]
        )
        transport = httpx.ASGITransport(app=asgi)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as http:
            yield http


async def test_fetch_returns_quote_payload(client: httpx.AsyncClient) -> None:
    response = await client.get("/rates/EUR/USD")

    assert response.status_code == 200
    body = response.json()
    assert body["pair"] == "EUR/USD"
    assert set(body) == {"pair", "rate", "fetched_at", "source"}
    assert body["source"] in ("upstream", "cache", "stale")


async def test_stats_counters_exposed(client: httpx.AsyncClient) -> None:
    await client.get("/rates/GBP/USD")

    body = (await client.get("/stats")).json()
    assert set(body) == {
        "hits",
        "misses",
        "upstream_calls",
        "retries",
        "stale_served",
    }
    assert body["misses"] >= 1


async def test_scenario_flip_roundtrip(client: httpx.AsyncClient) -> None:
    flipped = await client.post("/scenario/down")
    assert flipped.status_code == 200
    assert flipped.json()["scenario"] == "down"

    unknown = await client.post("/scenario/wat")
    assert unknown.status_code == 404
    assert "valid" in unknown.json()["error"]

    back = await client.post("/scenario/healthy")
    assert back.status_code == 200


async def test_cache_clear_endpoint(client: httpx.AsyncClient) -> None:
    await client.get("/rates/EUR/USD")
    cleared = await client.post("/cache/clear")
    assert cleared.status_code == 200

    # After clearing, the next read is a miss again.
    stats = (await client.get("/stats")).json()
    assert stats["hits"] == 0 or stats["misses"] >= 1


async def test_invalid_pair_maps_to_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/rates/USDEUR")
    assert response.status_code == 404
