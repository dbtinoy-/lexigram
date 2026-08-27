"""Pytest bootstrap + shared fixtures for the event-driven-orders demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install. Demo packages are intentionally
excluded from the monorepo aggregate test run (see root ``pyproject.toml``
``norecursedirs``), so these tests are run explicitly:

    uv run pytest demos/event-driven-orders/tests -q
"""
# Test fixture — boots the real composition root, resolves
# the WebProvider to get the Starlette ASGI app, then wraps it in
# httpx.AsyncClient for browser-like testing with cookie support.

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import os
import sys

import httpx
import pytest
from starlette.applications import Starlette

# Pin cwd to the demo root so application.yaml is discovered.
os.chdir(Path(__file__).resolve().parent.parent)

# Ensure the demo package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real composition root and expose its ASGI app.

    This boots the real application (not a mock) so tests exercise
    the full provider lifecycle: register → boot → serve → shutdown.
    """
    from orders.app import create_app

    application = create_app()
    await application.start()
    try:
        from lexigram.web import WebProvider

        # Resolve the WebProvider to get the Starlette ASGI app.
        # The framework's WebModule registers this during configure().
        web = await application.container.resolve(WebProvider)
        yield web.starlette
    finally:
        await application.stop()


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    """A browser session (own cookie jar) over the running app.

    Uses httpx.AsyncClient with ASGITransport for in-process testing
    — no real network calls.  Cookie jar maintains session state
    across requests, just like a real browser.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http:
        yield http


@pytest.fixture(autouse=True)
def _ensure_cwd() -> None:
    """Pin cwd to the demo root before every test."""
    os.chdir(_DEMO_ROOT)
