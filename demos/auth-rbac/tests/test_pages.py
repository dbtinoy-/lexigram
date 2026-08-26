"""Pages smoke tests for the RBAC console.

These are the *structural* half of the demo suite (behavioral tests in
``test_rbac.py``).  They verify that the page controller serves the
right HTML and static assets — no business logic exercised here.

Teaching note: smoke tests are cheap sanity checks that run fast and
catch wiring errors (missing routes, broken templates) before behavioral
tests dig into the details.
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        ("/login", "persona"),
        ("/matrix", "Permission matrix"),
    ],
)
async def test_pages_serve(
    client: httpx.AsyncClient, path: str, marker: str
) -> None:
    response = await client.get(path)
    assert response.status_code == 200
    assert marker in response.text
    assert "text/html" in response.headers["content-type"]


async def test_static_assets_served(client: httpx.AsyncClient) -> None:
    css = await client.get("/static/style.css")
    js = await client.get("/static/app.js")
    matrix_js = await client.get("/static/matrix.js")

    assert css.status_code == 200
    assert js.status_code == 200
    assert matrix_js.status_code == 200
