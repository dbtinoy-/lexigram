"""Pytest bootstrap for the RBAC console demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install:

    uv run pytest demos/auth-rbac/tests -q
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import sys

import httpx
import pytest
from rbac_console.module import RbacModule
from starlette.applications import Starlette

from lexigram.app import Application
from lexigram.web.di.provider import WebProvider

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real module graph and expose its ASGI app."""
    from rbac_console.config import load_lex_config

    async with Application.boot(
        name="rbac-console-test",
        modules=[RbacModule.configure()],
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


async def login_as(client: httpx.AsyncClient, persona: str) -> None:
    response = await client.post("/api/login", json={"persona": persona})
    assert response.status_code == 200, response.text
