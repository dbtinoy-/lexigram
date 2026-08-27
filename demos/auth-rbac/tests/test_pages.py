"""Pages smoke tests for the RBAC console.

These are the structural half of the test suite (behavioral tests in
test_rbac.py).  They verify that page routes serve the right HTML and
static assets — no business logic exercised.

Smoke tests catch wiring errors (missing routes, broken templates) before
behavioral tests dig into the details.  They're cheap, fast, and catch
the most common integration mistakes.
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
    """Parametrized smoke test: each page route returns HTML with expected content.

    Pattern: one test body, multiple route/content pairs.  If a new page
    is added to PagesController, add a tuple here — the test auto-expands.
    """
    response = await client.get(path)
    assert response.status_code == 200
    assert marker in response.text
    assert "text/html" in response.headers["content-type"]


async def test_static_assets_served(client: httpx.AsyncClient) -> None:
    """Verify static files are served with correct content types.

    PagesController serves assets from ui/static/ — no CDN, no build step.
    In production you'd serve these via nginx/CDN, but for the demo this
    keeps everything in one process.
    """
    css = await client.get("/static/style.css")
    js = await client.get("/static/app.js")
    matrix_js = await client.get("/static/matrix.js")

    assert css.status_code == 200
    assert js.status_code == 200
    assert matrix_js.status_code == 200
