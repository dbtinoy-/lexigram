"""Smoke tests for the playground page routes."""

from __future__ import annotations

import httpx


async def test_root_serves_playground(client: httpx.AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Guardrails Playground" in response.text
    for act in ("injection", "pii", "length", "model", "budget"):
        assert f'data-act="{act}"' in response.text


async def test_static_assets_served(client: httpx.AsyncClient) -> None:
    css = await client.get("/static/style.css")
    js = await client.get("/static/app.js")

    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]
