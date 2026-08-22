"""Pytest bootstrap for the support-agent demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import
``support_agent`` without installing (auth-web pattern):

    uv run pytest demos/support-agent/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from collections.abc import AsyncIterator

import httpx
import pytest
from starlette.applications import Starlette

from lexigram.app import Application
from lexigram.web.di.provider import WebProvider


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real module graph and expose its ASGI app."""
    from support_agent.module import SupportAgentModule

    async with Application.boot(
        name="support-agent-test",
        modules=[SupportAgentModule.configure()],
    ) as application:
        web = await application.container.resolve(WebProvider)
        yield web.starlette


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client over the running app (no socket bound)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http:
        yield http
