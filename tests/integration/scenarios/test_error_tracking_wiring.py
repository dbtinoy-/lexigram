from __future__ import annotations

"""Error-tracking wiring scenario: provider boot installs the unhandled hook.

Packages under test: lexigram-monitor
Infrastructure: none (external SDK is faked via ``sys.modules``)

Scenario:
1. Boot a minimal application with MonitorModule configured with a Sentry DSN.
2. Assert boot installed the unhandled-exception hook (``sys.excepthook``).
3. Raise an unhandled exception and assert it reaches the error tracker
   with the configured DSN, then restore the previous hook.
"""

import sys
from typing import Any

import pytest

from lexigram.app.base import Application
from lexigram.monitor import MonitorModule
from lexigram.monitor.config import ErrorTrackingConfig, MonitorConfig
from lexigram.monitor.error_tracking import UnhandledExceptionHook

pytestmark = [pytest.mark.integration, pytest.mark.scenario]


class _FakeSentry:
    """Minimal sentry_sdk-shaped fake recording init args and exceptions."""

    def __init__(self) -> None:
        self.init_kwargs: dict[str, Any] = {}
        self.captured: list[BaseException] = []

    def init(self, **kwargs: Any) -> None:
        """Record the kwargs passed to ``sentry_sdk.init``."""
        self.init_kwargs.update(kwargs)

    def capture_exception(self, exc: BaseException) -> None:
        """Record a captured exception."""
        self.captured.append(exc)

    def flush(self, timeout: float = 2.0) -> None:
        """No-op flush."""


class TestErrorTrackingWiring:
    """Monitor provider boot -> Sentry SDK init -> excepthook capture chain."""

    async def test_provider_boot_installs_hook_and_reports_exception(
        self, monkeypatch: Any
    ) -> None:
        """An unhandled exception raised after boot reaches the error tracker.

        A fake ``sentry_sdk`` module is injected before boot so the provider's
        conditional import resolves to the fake; the assertion then verifies
        the DSN was passed to ``sentry.init`` and the exception reached
        ``capture_exception``.

        Args:
            monkeypatch: Pytest monkeypatch for ``sys.modules`` injection.
        """
        fake_sentry = _FakeSentry()
        monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sentry)

        app = Application(name="error-tracking-scenario")
        app.add_modules(
            [
                MonitorModule.configure(
                    config=MonitorConfig(
                        error_tracking=ErrorTrackingConfig(
                            dsn="https://public@sentry.io/scenario"
                        )
                    )
                )
            ]
        )
        original_hook = sys.excepthook
        try:
            await app.start()
            try:
                assert isinstance(sys.excepthook, UnhandledExceptionHook)
                assert (
                    fake_sentry.init_kwargs["dsn"]
                    == "https://public@sentry.io/scenario"
                )

                sys.excepthook(ValueError, ValueError("boom"), None)

                assert len(fake_sentry.captured) == 1
                assert str(fake_sentry.captured[0]) == "boom"
            finally:
                hook = sys.excepthook
                if isinstance(hook, UnhandledExceptionHook):
                    hook.uninstall()
                await app.stop()
        finally:
            sys.excepthook = original_hook
