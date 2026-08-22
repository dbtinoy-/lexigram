"""Pytest bootstrap for the feedback-loop demo (single shim — no UI).

    uv run pytest demos/feedback-loop/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pytest


@pytest.fixture
async def service(tmp_path):
    """Boot the module graph with tmp experiment dir; yield LoopService."""
    from lexigram.app import Application

    from feedback_loop.loop_service import LoopService
    from feedback_loop.module import FeedbackLoopModule

    async with Application.boot(
        name="feedback-loop-test",
        modules=[FeedbackLoopModule.configure(experiment_dir=str(tmp_path))],
    ) as application:
        yield await application.container.resolve(LoopService)
