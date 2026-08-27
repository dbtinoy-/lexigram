"""Composition root for the rag-docs demo — start reading here.

Every Lexigram application has exactly one place that knows how the pieces
fit together: the **composition root**.  Everything else (controllers,
services, templates) is inert until *this file* wires it.

The mental model has three layers.  Once these click, every Lexigram app
reads the same way:

┌─────────────────────────────────────────────────────────────────────────┐
│ 1. CONFIGURATION                                                        │
│    ``application.yaml`` holds your values.  The framework loads it,     │
│    merges overrides on top (highest → lowest):                          │
│                                                                         │
│        LEX_WEB__SERVER__PORT=9000   env vars   ← win over everything    │
│        application.production.yaml  profile overlay                     │
│        application.yaml             base file                           │
│        dataclass field defaults     last resort                         │
│                                                                         │
│    Result: ONE typed ``LexigramConfig`` object.                         │
│                                                                         │
│ 2. CAPABILITIES (declarative)                                           │
│    ``Module.configure(...)`` switches framework packages on and tells   │
│    them which controllers are yours.  Each package reads its own yaml   │
│    section through its config model.                                    │
│                                                                         │
│ 3. SERVICES (imperative)                                               │
│    A ``Provider`` registers the services *you* wrote into the DI        │
│    container, with register/boot/shutdown lifecycle hooks.              │
└─────────────────────────────────────────────────────────────────────────┘

This demo's lesson is the RAG pipeline: ``DocsAskProvider.boot`` ingests the
markdown corpus, chunks + embeds it into a vector collection (one shared
embedder so query vectors reuse the corpus IDF weights), and assembles the
ask service with retrieval strategies and an extractive synthesizer.  Index
building happens once, at boot — request handling is retrieve + synthesize.

Run with ``uv run python -m rag_docs``.
"""

from __future__ import annotations

from lexigram.app.base import Application  # Application = the bootable object
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider  # base class for your DI registrations
from lexigram.web.module import WebModule  # framework module — owns web server
from rag_docs.controllers.api import DocsAskApiController  # your HTTP surface
from rag_docs.di.provider import DocsAskProvider  # your service registrations
from rag_docs.ui.pages import DocsPageController  # page controller (optional)


def build_modules() -> list[object]:
    """Declarative capabilities — zero configuration arguments needed.

    Each ``Module.configure(...)`` returns a DynamicModule: a recipe the
    framework expands into providers at boot.  Because every provider in
    the bundle declares ``config_key`` / ``config_model``, the orchestrator
    injects the matching typed section of ``LexigramConfig`` into
    ``provider.config`` right before ``register()`` runs — YAML values and
    ``LEX_*`` environment overrides already merged.
    """
    return [
        # WebModule is the only module that needs your controllers list —
        # this is the explicit wiring style.  Omit DocsPageController if you
        # use an external frontend (React, Vue, etc.).
        WebModule.configure(
            controllers=[DocsAskApiController, DocsPageController],
        ),
    ]


def build_providers(docs_dir: Path | None = None) -> list[Provider]:
    """Imperative services owned by this demo.

    A Provider is Lexigram's unit of lifecycle management: ``register()``
    binds services into the DI container, ``boot()`` runs post-registration
    setup (here: ingest the corpus and build the vector index), ``shutdown()``
    cleans up.

    ``docs_dir`` overrides the indexed corpus; ``None`` keeps the provider's
    CWD-proof default (the repository's real ``docs/`` directory).
    """
    return [DocsAskProvider(docs_dir=docs_dir)]


def create_app(
    docs_dir: Path | None = None,
    config: LexigramConfig | None = None,
) -> Application:
    """Create the application in ``CREATED`` state (not yet started).

    Use this directly in tests (boot it yourself so you control the
    lifecycle) or hand the pieces to :meth:`Application.boot` as
    ``main.serve`` does — the context manager guarantees ``stop()`` even
    when something raises.

    Args:
        docs_dir: Optional corpus override forwarded to the provider.
        config: Optional pre-loaded config. When ``None`` the framework
            auto-discovers ``application.yaml`` from the working directory.
    """
    # Application is created in CREATED state — not yet started.
    # Modules declare capabilities; providers fill services.
    # The dependency graph resolves lazily at boot.
    app = Application(name="rag-docs", config=config)
    app.add_modules(build_modules())
    app.add_providers(build_providers(docs_dir))
    return app


from pathlib import Path  # noqa: E402 — placed after class to avoid circular

__all__ = ["build_modules", "build_providers", "create_app"]
