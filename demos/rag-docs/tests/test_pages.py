"""Smoke tests for the docs console page routes."""

from __future__ import annotations

import httpx
import pytest


@pytest.fixture
async def client():
    from lexigram.app import Application
    from lexigram.web.di.provider import WebProvider

    from rag_docs.module import DocsAskModule

    async with Application.boot(
        name="rag-docs-pages-test",
        modules=[DocsAskModule.configure()],
    ) as application:
        web = await application.container.resolve(WebProvider)
        transport = httpx.ASGITransport(app=web.starlette)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as http:
            yield http


async def test_root_serves_console(client: httpx.AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "RAG Docs" in response.text


async def test_static_assets_served(client: httpx.AsyncClient) -> None:
    css = await client.get("/static/style.css")
    js = await client.get("/static/app.js")

    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]
