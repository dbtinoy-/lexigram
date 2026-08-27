"""Smoke tests for the memory chat page routes."""

from __future__ import annotations

import httpx

async def test_root_serves_chat(client: httpx.AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Memory Chat" in response.text
    assert 'data-owner="alice"' in response.text
    assert 'data-owner="bob"' in response.text

    response = await client.get("/")

    assert response.status_code == 200

async def test_page_has_light_theme(client: httpx.AsyncClient) -> None:
    css = await client.get("/static/style.css")

    assert css.status_code == 200
    assert "#f8f9fa" in css.text or "#ffffff" in css.text

async def test_page_has_footer(client: httpx.AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert "demo-footer" in response.text
    assert "lexigram.dev" in response.text

async def test_static_assets_served(client: httpx.AsyncClient) -> None:
    css = await client.get("/static/style.css")
    js = await client.get("/static/app.js")

    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]
