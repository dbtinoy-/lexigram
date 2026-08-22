"""Pytest bootstrap for the feedback-loop demo (single shim — no UI).

uv run pytest demos/feedback-loop/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import httpx
import pytest
from starlette.applications import Starlette

from lexigram.app import Application
from lexigram.web.di.provider import WebProvider


@pytest.fixture
async def service(tmp_path):
    """Boot the module graph with tmp experiment dir; yield LoopService."""
    from feedback_loop.module import FeedbackLoopModule
    from feedback_loop.services.loop_service import LoopService

    from lexigram.app import Application

    async with Application.boot(
        name="feedback-loop-test",
        modules=[FeedbackLoopModule.configure(experiment_dir=str(tmp_path))],
    ) as application:
        yield await application.container.resolve(LoopService)


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real module graph and expose its ASGI app."""
    import tempfile

    from feedback_loop.module import FeedbackLoopModule

    tmp = tempfile.mkdtemp(prefix="fl-runs-")
    async with Application.boot(
        name="feedback-loop-web-test",
        modules=[FeedbackLoopModule.configure(experiment_dir=tmp)],
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
