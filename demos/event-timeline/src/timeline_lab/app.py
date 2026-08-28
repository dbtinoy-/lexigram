"""Composition root for the focused Events Timeline / Replay Lab."""

from __future__ import annotations

from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider
from lexigram.events.module import EventsModule
from lexigram.web.module import WebModule
from timeline_lab.controllers.api import TimelineApiController
from timeline_lab.di.provider import TimelineLabProvider
from timeline_lab.ui.pages import TimelinePageController


def build_modules() -> list[object]:
    """Enable only the package under test and its browser transport."""
    return [
        EventsModule.configure(),
        WebModule.configure(
            controllers=[TimelineApiController, TimelinePageController],
        ),
    ]


def build_providers() -> list[Provider]:
    """Register the demo scenario's lifecycle wiring."""
    return [TimelineLabProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create an unstarted application for standalone use and tests."""
    application = Application(name="event-timeline", config=config)
    application.add_modules(build_modules())
    application.add_providers(build_providers())
    return application


__all__ = ["build_modules", "build_providers", "create_app"]
