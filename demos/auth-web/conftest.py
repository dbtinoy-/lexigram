"""Pytest bootstrap for the auth web demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install:

    uv run pytest demos/auth-web/tests -q
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import sys

from auth_web.module import AuthWebModule
import httpx
import pytest
from starlette.applications import Starlette

from lexigram.app import Application
from lexigram.web.di.provider import WebProvider

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real module graph and expose its ASGI app."""
    async with Application.boot(
        name="auth-web-test", modules=[AuthWebModule.configure()]
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


def second_browser(app: Starlette) -> httpx.AsyncClient:
    """An independent browser (own cookie jar) over the same running app."""
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )
