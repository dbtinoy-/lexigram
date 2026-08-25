"""Application composition root for the rag-docs demo.

``create_app`` is the only place that knows how the modules fit together;
sections are bound inline from the demo's ``application.yaml``.
"""

from __future__ import annotations

from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from rag_docs.config import load_lex_config
from rag_docs.controllers.api import DocsAskApiController
from rag_docs.di.provider import DocsAskProvider
from rag_docs.pages import DocsPageController


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) application."""
    config = config or load_lex_config()
    web_config = config.get_section("web", WebConfig)

    app = Application(name="rag-docs", config=config)
    app.add_modules(
        [
            WebModule.configure(
                web_config=web_config,
                controllers=[DocsAskApiController, DocsPageController],
            ),
        ]
    )
    app.add_provider(DocsAskProvider())
    return app


__all__ = ["create_app"]
