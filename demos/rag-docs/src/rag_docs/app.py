"""Application composition root for the rag-docs demo."""

from __future__ import annotations

from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from rag_docs.config import load_lex_config
from rag_docs.controllers.api import DocsAskApiController
from rag_docs.di.provider import DocsAskProvider
from rag_docs.ui.pages import DocsPageController


def create_app(
    config: LexigramConfig | None = None,
    docs_dir: Path | None = None,
) -> Application:
    """Create the configured (not yet started) rag-docs application.

    Args:
        config: Explicit configuration; defaults to the demo's yaml.
        docs_dir: Optional corpus override forwarded to the provider.
    """
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
    app.add_provider(DocsAskProvider(docs_dir=docs_dir))
    return app


__all__ = ["create_app"]
