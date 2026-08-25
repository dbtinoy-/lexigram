"""REST endpoint tests for the rag-docs demo.

Boots the composition root (corpus ingestion at boot included) and
which ingests the corpus at boot — and drives the real routes via an
``httpx.AsyncClient`` over the framework's ASGI app.
"""

from __future__ import annotations

from typing import AsyncIterator

import httpx
import pytest

from lexigram.web.di.provider import WebProvider

from rag_docs.app import create_app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    application = create_app()
    await application.start()
    try:
        web = await application.container.resolve(WebProvider)
        transport = httpx.ASGITransport(app=web.starlette)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as http:
            yield http
    finally:
        await application.stop()


from lexigram.web.di.provider import WebProvider

from rag_docs.app import create_app  # noqa: E402  (after sys.path setup)


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
    assert "strategy" in response.json()["detail"].lower()


async def test_missing_question_maps_to_422(client: httpx.AsyncClient) -> None:
    response = await client.post("/ask", json={})

    assert response.status_code == 422
    assert "question is required" in response.json()["detail"]


async def test_stats_reports_corpus_stats(client: httpx.AsyncClient) -> None:
    response = await client.get("/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["files"] > 0
    assert body["chunks"] >= body["files"]
