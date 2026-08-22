"""Pytest bootstrap for the prompt-lab demo.

Adds the demo's ``src`` directory to ``sys.path`` (auth-web pattern):

    uv run pytest demos/prompt-lab/tests -q
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
    from prompt_lab.module import PromptLabModule

    async with Application.boot(
        name="prompt-lab-test",
        modules=[PromptLabModule.configure()],
    ) as application:
        web = await application.container.resolve(WebProvider)
        yield web.starlette


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http:
        yield http
