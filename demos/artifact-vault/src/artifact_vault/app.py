"""Composition root for the single-niche Artifact Vault demo."""

from __future__ import annotations

from artifact_vault.controllers.api import ArtifactVaultApiController
from artifact_vault.di.provider import ArtifactVaultProvider
from artifact_vault.ui.pages import ArtifactVaultPageController
from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider
from lexigram.storage.module import StorageModule
from lexigram.web.module import WebModule


def build_modules() -> list[object]:
    return [
        StorageModule.configure(),
        WebModule.configure(
            controllers=[ArtifactVaultApiController, ArtifactVaultPageController],
        ),
    ]


def build_providers() -> list[Provider]:
    return [ArtifactVaultProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    app = Application(name="artifact-vault", config=config)
    app.add_modules(build_modules())
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
