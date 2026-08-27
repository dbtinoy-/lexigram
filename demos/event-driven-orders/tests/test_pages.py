"""Page controller tests for the event-driven-orders demo."""

from __future__ import annotations

import httpx


async def test_console_renders(client: httpx.AsyncClient) -> None:
    r = await client.get("/")
    assert r.status_code == 200
    assert "Event-Driven Orders" in r.text


async def test_console_has_logo(client: httpx.AsyncClient) -> None:
    r = await client.get("/")
    assert "/static/logo.png" in r.text


async def test_console_has_light_theme(client: httpx.AsyncClient) -> None:
    css = await client.get("/static/style.css")
    assert css.status_code == 200
    assert "#f8f9fa" in css.text


async def test_console_has_footer(client: httpx.AsyncClient) -> None:
    r = await client.get("/")
    assert "demo-footer" in r.text
    assert "lexigram.dev" in r.text


async def test_css_returns(client: httpx.AsyncClient) -> None:
    r = await client.get("/static/style.css")
    assert r.status_code == 200


async def test_logo_returns_png(client: httpx.AsyncClient) -> None:
    r = await client.get("/static/logo.png")
    assert r.status_code == 200
    assert "image/png" in r.headers["content-type"]


async def test_js_returns(client: httpx.AsyncClient) -> None:
    r = await client.get("/static/app.js")
    assert r.status_code == 200
