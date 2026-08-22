"""Pytest bootstrap + shared fixtures for the API-keys console demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install:

    uv run pytest demos/auth-apikeys/tests -q
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import sys

import httpx
import pytest
from starlette.applications import Starlette

from lexigram.app import Application
from lexigram.web.di.provider import WebProvider

from apikey_console.module import ApiKeysModule

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real module graph and expose its ASGI app."""
    async with Application.boot(
        name="apikeys-console-test", modules=[ApiKeysModule.configure()]
    ) as application:
        web = await application.container.resolve(WebProvider)
        yield web.starlette


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    """A browser session (own cookie jar) over the running app."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http:
        yield http
