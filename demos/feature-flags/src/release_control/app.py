"""Composition root for Release Control Lab.

This is a single-package niche demo: ``FeatureFlagsModule`` owns flag
infrastructure and ``WebModule`` owns the HTTP surface. The local provider
only adapts package-owned services for a visual release-operations console.
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
    return [
        FeatureFlagsModule.configure(),
        WebModule.configure(
            controllers=[ReleaseControlApiController, ReleaseControlPageController],
        ),
    ]


def build_providers() -> list[Provider]:
    return [ReleaseControlProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    app = Application(name="feature-flags", config=config)
    app.add_modules(build_modules())
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
