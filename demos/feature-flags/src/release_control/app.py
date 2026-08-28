"""Composition root for Release Control Lab.

This is a single-package niche demo: ``FeatureFlagsModule`` owns the rich
flag definitions and evaluation infrastructure, while ``WebModule`` owns the
HTTP surface. The application layer only presents those package-owned APIs in
a visual release-operations console.
"""

from __future__ import annotations

from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider
from lexigram.features.module import FeatureFlagsModule
from lexigram.web.module import WebModule
from release_control.controllers.api import ReleaseControlApiController
from release_control.di.provider import ReleaseControlProvider
from release_control.ui.pages import ReleaseControlPageController


def build_modules() -> list[object]:
    """Build the Lexigram modules required by the release control demo."""
    return [
        FeatureFlagsModule.configure(),
        WebModule.configure(
            controllers=[ReleaseControlApiController, ReleaseControlPageController],
        ),
    ]


def build_providers() -> list[Provider]:
    """Build the DI providers for the release control demo."""
    return [ReleaseControlProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create and configure the release control application."""
    app = Application(name="feature-flags", config=config)
    app.add_modules(build_modules())
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
