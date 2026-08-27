"""Pytest bootstrap for the RBAC console demo.

Two jobs:

1. Make imports and config discovery work regardless of *where* pytest is
   invoked: chdir into this demo's root (where ``application.yaml`` lives)
   and put ``src`` on ``sys.path``. The framework auto-discovers
   ``application.yaml`` from the working directory, so after this chdir no
   custom configuration loader is needed anywhere.
2. Boot the real composition root for tests via fixtures.

    uv run pytest demos/auth-rbac/tests -q        # from repo root works too
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import os
import sys

import httpx
import pytest
from starlette.applications import Starlette

_DEMO_ROOT = Path(__file__).resolve().parent.parent

# Lexigram discovers application.yaml from cwd — pin it so tests work
# from any invocation point (repo root or in-demo).
os.chdir(_DEMO_ROOT)
# Add src/ to sys.path so ``from rbac_console...`` resolves in tests.
sys.path.insert(0, str(_DEMO_ROOT / "src"))

from lexigram.web import WebProvider  # noqa: E402
from rbac_console.app import create_app  # noqa: E402 — after sys.path setup


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real composition root; yield the Starlette ASGI app.

    Manual start/stop (instead of Application.boot) because tests want
    to inspect the container while the server is running.  The lifecycle:
    register → freeze → boot (seeding) → yield → stop.
    """
    application = create_app()
    await application.start()
    try:
        # Resolve the WebProvider to get the underlying Starlette app.
        # WebProvider is a framework provider — it owns the ASGI server.
        web = await application.container.resolve(WebProvider)
        yield web.starlette
    finally:
        await application.stop()


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client bound to the app with a cookie jar per test.

    ASGITransport talks directly to the ASGI app in-process — no network.
    The cookie jar persists across requests within one test, exactly like
    a browser session, so login → protected-route flows work.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http:
        yield http


async def login_as(client: httpx.AsyncClient, persona: str) -> None:
    """Helper: POST /api/login as a persona.  Used by multiple test files."""
    response = await client.post("/api/login", json={"persona": persona})
    assert response.status_code == 200, response.text


@pytest.fixture(autouse=True)
def _ensure_cwd() -> None:
    """Pin cwd to the demo root before every test."""
    os.chdir(_DEMO_ROOT)
