"""Smoke tests for the static UI page routes."""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        ("/login", "Log in"),
        ("/register", "Register"),
        ("/profile", "Profile"),
        ("/password", "Change password"),
    ],
)
async def test_page_serves_html(
    client: httpx.AsyncClient, path: str, marker: str
) -> None:
    response = await client.get(path)
    assert response.status_code == 200
    assert marker in response.text
    assert "text/html" in response.headers["content-type"]


async def test_static_assets_served(client: httpx.AsyncClient) -> None:
    css = await client.get("/static/style.css")
    js = await client.get("/static/app.js")

    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]


async def test_index_redirects(client: httpx.AsyncClient) -> None:
    response = await client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/login"
