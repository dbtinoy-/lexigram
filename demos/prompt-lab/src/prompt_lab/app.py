"""Composition root for the prompt-lab demo.

Every Lexigram application has exactly one place that knows how the pieces
fit together — the **composition root** — and here it is deliberately tiny:

1. **Capabilities**: framework ``Module.configure(...)`` bundles. Each
   framework package reads its own section of ``application.yaml`` through
   provider auto-injection (``config_key`` / ``config_model``), so you pass
   *nothing* — just list the controllers your app contributes.
2. **Services**: this demo's own ``Provider`` (imperative register/boot
   lifecycle for stateful services — see ``di/provider.py``).

This demo's lesson is prompt templates under version control:
``PromptModule`` supplies template rendering contracts, while ``LabProvider``
seeds seeded template revisions into a bounded version store at registration
and assembles the A/B runner over them at boot — so every variant render and
comparison flows through versioned, resolvable services.

Run with ``uv run python -m prompt_lab``.
"""

from __future__ import annotations

from lexigram.ai.prompt.module import PromptModule
from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from prompt_lab.config import load_lex_config
from prompt_lab.controllers.api import LabApiController
from prompt_lab.di.provider import LabProvider
from prompt_lab.ui.pages import LabPageController


def build_modules(config: LexigramConfig) -> list[object]:
    """Declarative capabilities — framework modules bound to typed sections.

    ``config`` stays explicit here because demos live in subdirectories:
    binding against this demo's own ``application.yaml`` (absolute path)
    keeps behavior identical no matter the caller's working directory.
    """
    return [
        # Defaults are fine here: rendering happens through the module's
        # PromptTemplateProtocol binding, not through demo code.
        PromptModule.configure(),
        WebModule.configure(
            web_config=config.get_section("web", WebConfig),
            controllers=[LabApiController, LabPageController],
        ),
    ]


def build_providers() -> list[Provider]:
    """Imperative services owned by this demo."""
    return [LabProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the application in ``CREATED`` state (not yet started).

    Programmatic/tests entry point. For serving, prefer the idiomatic
    ``Application.boot(...)`` context manager shown in ``main.serve`` —
    it guarantees ``stop()`` even on exceptions or Ctrl-C.
    """
    config = config or load_lex_config()
    app = Application(name="prompt-lab", config=config)
    app.add_modules(build_modules(config))
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
