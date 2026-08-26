"""Composition root for the rag-docs demo.

Every Lexigram application has exactly one place that knows how the pieces
fit together — the **composition root** — and here it is deliberately tiny:

1. **Capabilities**: framework ``Module.configure(...)`` bundles. Each
   framework package reads its own section of ``application.yaml`` through
   provider auto-injection (``config_key`` / ``config_model``), so you pass
   *nothing* — just list the controllers your app contributes.
2. **Services**: this demo's own ``Provider`` (imperative register/boot
   lifecycle for stateful services — see ``di/provider.py``).

This demo's lesson is the RAG pipeline: ``DocsAskProvider.boot`` ingests the
markdown corpus, chunks + embeds it into a vector collection (one shared
embedder so query vectors reuse the corpus IDF weights), and assembles the
ask service with retrieval strategies and an extractive synthesizer. Index
building happens once, at boot — request handling is retrieve + synthesize.

Run with ``uv run python -m rag_docs serve``.
"""

from __future__ import annotations

from pathlib import Path

from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from rag_docs.config import load_lex_config
from rag_docs.controllers.api import DocsAskApiController
from rag_docs.di.provider import DocsAskProvider
from rag_docs.ui.pages import DocsPageController


def build_modules(config: LexigramConfig) -> list[object]:
    """Declarative capabilities — framework modules bound to typed sections.

    ``config`` stays explicit here because demos live in subdirectories:
    binding against this demo's own ``application.yaml`` (absolute path)
    keeps behavior identical no matter the caller's working directory.
    """
    return [
        WebModule.configure(
            web_config=config.get_section("web", WebConfig),
            controllers=[DocsAskApiController, DocsPageController],
        ),
    ]


def build_providers(docs_dir: Path | None = None) -> list[Provider]:
    """Imperative services owned by this demo.

    ``docs_dir`` overrides the indexed corpus; ``None`` keeps the provider's
    CWD-proof default (the repository's real ``docs/`` directory).
    """
    return [DocsAskProvider(docs_dir=docs_dir)]


def create_app(
    config: LexigramConfig | None = None,
    docs_dir: Path | None = None,
) -> Application:
    """Create the application in ``CREATED`` state (not yet started).

    Programmatic/tests entry point. For serving, prefer the idiomatic
    ``Application.boot(...)`` context manager shown in ``main.serve`` —
    it guarantees ``stop()`` even on exceptions or Ctrl-C.

    Args:
        config: Explicit configuration; defaults to the demo's yaml.
        docs_dir: Optional corpus override forwarded to the provider.
    """
    config = config or load_lex_config()
    app = Application(name="rag-docs", config=config)
    app.add_modules(build_modules(config))
    app.add_providers(build_providers(docs_dir))
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
