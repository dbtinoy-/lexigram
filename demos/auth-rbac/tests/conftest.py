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

# Framework config discovery is cwd-based; pin it to this demo so both
# `pytest demos/auth-rbac` (repo root) and in-dir runs behave identically.
os.chdir(_DEMO_ROOT)
sys.path.insert(0, str(_DEMO_ROOT / "src"))

from lexigram.web.di.provider import WebProvider  # noqa: E402
from rbac_console.app import create_app  # noqa: E402 — after sys.path setup


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real composition root and expose its ASGI app."""
    application = create_app()
    await application.start()
    try:
        
        web = await application.container.resolve(WebProvider)
        yield web.starlette
    finally:
        await application.stop()


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    """A browser session (own cookie jar) over the running app."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http:
        yield http


async def login_as(client: httpx.AsyncClient, persona: str) -> None:
    response = await client.post("/api/login", json={"persona": persona})
    assert response.status_code == 200, response.text
