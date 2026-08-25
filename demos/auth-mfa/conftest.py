"""Pytest bootstrap + shared fixtures for the MFA console demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install:

    uv run pytest demos/auth-mfa/tests -q
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import sys

import httpx
from mfa_console.module import MfaModule
import pytest
from starlette.applications import Starlette

from lexigram.app import Application
from lexigram.web.di.provider import WebProvider

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mfa_console.config import load_lex_config  # noqa: E402


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real module graph and expose its ASGI app."""
    async with Application.boot(
        name="mfa-console-test",
        modules=[MfaModule.configure()],
        config=load_lex_config(),
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
