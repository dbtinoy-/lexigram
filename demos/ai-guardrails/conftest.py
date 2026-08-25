"""Pytest bootstrap for the ai-guardrails demo.

Adds the demo's ``src`` directory to ``sys.path`` (auth-web pattern):

    uv run pytest demos/ai-guardrails/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from collections.abc import AsyncIterator

import httpx
import pytest
from starlette.applications import Starlette

from lexigram.web.di.provider import WebProvider


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real composition root and expose its ASGI app."""
    from guard_gate.app import create_app
    from guard_gate.config import load_lex_config

    application = create_app(load_lex_config())
    await application.start()
    try:
        web = await application.container.resolve(WebProvider)
        yield web.starlette
    finally:
        await application.stop()


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http:
        yield http
