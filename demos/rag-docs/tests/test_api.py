"""REST endpoint tests for the rag-docs demo.

Boots ``DocsAskModule`` (web wiring included) through the real container —
which ingests the corpus at boot — resolves the controller, and drives its
routes via an ``httpx.AsyncClient`` over a minimal Starlette app.
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

from rag_docs.controllers.api import DocsAskApiController
from rag_docs.module import DocsAskModule


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with Application.boot(
        name="rag-api-test", modules=[DocsAskModule.configure()]
    ) as app:
        controller = await app.container.resolve(DocsAskApiController)

        def json(handler):
            async def endpoint(request: Request) -> JSONResponse:
                result = await handler(request)
                if isinstance(result, JSONResponse):
                    return result
                return JSONResponse(result)

            return endpoint

        asgi = Starlette(
            routes=[
                Route("/ask", json(controller.ask), methods=["POST"]),
                Route("/stats", json(controller.health), methods=["GET"]),
            ]
        )
        transport = httpx.ASGITransport(app=asgi)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as http:
            yield http


async def test_ask_returns_answer_with_citations(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/ask", json={"question": "how do modules export services?"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert isinstance(body["citations"], list)


async def test_ask_supports_mmr_strategy(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/ask",
        json={
            "question": "what do providers register?",
            "strategy": "mmr",
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"]


async def test_unknown_strategy_maps_to_400(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/ask",
        json={"question": "anything", "strategy": "bogus"},
    )

    assert response.status_code == 400
    assert "strategy" in response.json()["error"].lower()


async def test_missing_question_maps_to_400(client: httpx.AsyncClient) -> None:
    response = await client.post("/ask", json={})

    assert response.status_code == 400


async def test_stats_reports_corpus_stats(client: httpx.AsyncClient) -> None:
    response = await client.get("/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["files"] > 0
    assert body["chunks"] >= body["files"]
