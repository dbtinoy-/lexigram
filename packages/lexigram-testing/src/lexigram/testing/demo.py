"""Shared helpers for demo application test suites.

Blueprint Task B: replaces the per-demo ``conftest.py`` boilerplate
(sys.path bootstrap, boot/teardown fixture, structlog-freeze for
``capture_logs`` tests) with one import.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Callable

import pytest


def install_demo_src(conftest: str | Path) -> None:
    """Put the demo's ``src`` directory on ``sys.path``.

    Args:
        conftest: ``__file__`` of the calling conftest; the sibling ``src``
            directory is inserted at ``sys.path[0]``.
    """
    src = Path(conftest).resolve().parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def freeze_logging_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep structlog processors stable across ``Application.start()``.

    Boot applies ``LoggingConfig`` and replaces the processor chain, which
    silently detaches ``structlog.testing.capture_logs`` mid-test. Tests that
    narrate through structured events should request this fixture.
    """
    from lexigram.app import base as app_base

    monkeypatch.setattr(app_base, "_apply_logging_config", lambda _cfg: None)


def make_app_fixture(
    create_app: Callable[..., Any],
) -> Callable[[Any], AsyncIterator[Any]]:
    """Build a standard ``app`` fixture from a demo composition root.

    The returned fixture boots the application, yields it, and stops it in
    teardown — mirroring ``main.serve`` without binding a socket.

    Args:
        create_app: The demo's composition root callable.

    Returns:
        An async pytest fixture yielding a started ``Application``.
    """

    @pytest.fixture
    async def app() -> AsyncIterator[Any]:
        application = create_app()
        await application.start()
        try:
            yield application
        finally:
            await application.stop()

    return app
