"""Pytest bootstrap for the ai-guardrails demo.

1. Chdir into this demo's root so ``application.yaml`` is discovered.
2. Add ``src`` to ``sys.path`` for imports.
3. Boot the real composition root via fixtures.

This conftest boots the FULL application stack — no mocks.
This is the Lexigram integration testing pattern: use the real DI
container, real providers, real services.  Tests validate the entire
wiring, not just individual units.  For unit tests, mock at the
protocol boundary (e.g. mock GuardPipelineProtocol).
"""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from starlette.applications import Starlette

_DEMO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(_DEMO_ROOT)
sys.path.insert(0, str(_DEMO_ROOT / "src"))

from guard_gate.app import create_app  # noqa: E402
from lexigram.web import WebProvider  # noqa: E402


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real composition root; yield the Starlette ASGI app.

    create_app() returns an Application in CREATED state.
    await app.start() triggers the full provider lifecycle:
    register() all providers → freeze container → boot() all providers.

    We resolve WebProvider to get the underlying Starlette instance
    for httpx transport.  In production, run_server_async handles this.
    """
    application = create_app()
    await application.start()
    try:
        web = await application.container.resolve(WebProvider)
        yield web.starlette
    finally:
        await application.stop()


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client bound to the app with a cookie jar per test.

    ASGITransport lets httpx talk directly to the ASGI app
    without a real TCP server.  This is faster and more reliable for
    testing than spinning up uvicorn.  base_url="http://testserver"
    is required by httpx for routing.
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
