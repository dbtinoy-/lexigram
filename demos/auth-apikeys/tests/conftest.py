"""Pytest bootstrap + shared fixtures for the api-keys demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install:

    cd demos/auth-apikeys
    uv run pytest tests -q
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
    """Boot the real composition root and expose its ASGI app."""
    # Real composition root in tests — no mocking.
    # The app boots exactly as in production; in-memory repos are
    # used automatically. This validates the full wiring.
    from apikey_console.app import create_app

    application = create_app()
    await application.start()
    try:
        from lexigram.web import WebProvider

        web = await application.container.resolve(WebProvider)
        yield web.starlette
    finally:
        await application.stop()


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    """A browser session (own cookie jar) over the running app."""
    # ASGITransport — httpx talks directly to the ASGI
    # app in-process. No real server needed. Each client gets its own
    # cookie jar, simulating independent browser sessions.
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http:
        yield http


@pytest.fixture(autouse=True)
def _ensure_cwd() -> None:
    """Pin cwd to the demo root before every test."""
    os.chdir(_DEMO_ROOT)
