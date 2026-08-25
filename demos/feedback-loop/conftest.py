"""Pytest bootstrap for the feedback-loop demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install:

    uv run pytest demos/feedback-loop/tests -q
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import sys
import tempfile

import httpx
import pytest
from starlette.applications import Starlette

from lexigram.web.di.provider import WebProvider

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from feedback_loop.app import create_app  # noqa: E402
from feedback_loop.config import load_lex_config  # noqa: E402
from feedback_loop.services.loop_service import LoopService  # noqa: E402


@pytest.fixture
async def service(tmp_path) -> AsyncIterator[LoopService]:
    """Boot with a tmp experiment dir; yield the loop service."""
    config = load_lex_config()
    app = create_app(config)
    try:
        await app.start()
        yield await app.container.resolve(LoopService)
    finally:
        await app.stop()


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real composition root and expose its ASGI app."""
    tmp = tempfile.mkdtemp(prefix="fl-runs-")
    config = load_lex_config()
    app = create_app(config)
    try:
        await app.start()
        web = await app.container.resolve(WebProvider)
        yield web.starlette
    finally:
        await app.stop()


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http:
        yield http
