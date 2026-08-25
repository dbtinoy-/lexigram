"""Pytest bootstrap + shared fixtures for the API-keys console demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install:

    uv run pytest demos/auth-apikeys/tests -q
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import sys

from apikey_console.app import create_app
import httpx
import pytest
from starlette.applications import Starlette

from lexigram.web.di.provider import WebProvider

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import os  # noqa: E402

os.chdir(Path(__file__).resolve().parent)


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real composition root and expose its ASGI app."""
    from apikey_console.config import load_lex_config

    application = create_app(load_lex_config())
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
