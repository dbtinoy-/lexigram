"""Pytest bootstrap for the prompt-lab demo.

Sets the working directory to the demo root so ``application.yaml`` is
discovered automatically, then adds ``src/`` to ``sys.path`` for imports.

Run::

    uv run pytest demos/prompt-lab/tests -q
"""

from __future__ import annotations

from collections.abc import AsyncIterator
import os
from pathlib import Path
import sys

import httpx
import pytest
from starlette.applications import Starlette

_DEMO_ROOT = Path(__file__).resolve().parent
os.chdir(_DEMO_ROOT)
sys.path.insert(0, str(_DEMO_ROOT / "src"))

from lexigram.web.di.provider import WebProvider  # noqa: E402


@pytest.fixture(autouse=True)
def _ensure_cwd() -> None:
    """Pin cwd to the demo root before every test."""
    os.chdir(_DEMO_ROOT)


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real composition root and expose its ASGI app."""
    from prompt_lab.app import create_app

    application = create_app()
    await application.start()
    try:
        web = await application.container.resolve(WebProvider)
        yield web.starlette
    finally:
        await application.stop()


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    """Async HTTP client wired to the in-process ASGI app."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http:
        yield http
