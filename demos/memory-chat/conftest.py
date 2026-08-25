"""Pytest bootstrap for the memory-chat demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import
``memory_chat`` without installing (auth-web pattern):

    uv run pytest demos/memory-chat/tests -q
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
    from memory_chat.app import create_app
    from memory_chat.config import load_lex_config

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


from datetime import UTC, datetime

from lexigram.primitives import clock
from lexigram.testing.clock import FixedClock

_TURN_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _fixed_clock():
    """Pin the ambient clock so entries stay byte-deterministic."""
    with clock.use(FixedClock(_TURN_EPOCH)):
        yield
