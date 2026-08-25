"""Application composition root for the memory-chat demo."""

from __future__ import annotations

from lexigram.ai.memory import MemoryConfig, MemoryModule
from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from memory_chat.config import load_lex_config
from memory_chat.controllers.api import ConciergeApiController
from memory_chat.di.provider import ConciergeProvider
from memory_chat.ui.pages import ChatPageController


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) memory-chat application."""
    config = config or load_lex_config()
    web_config = config.get_section("web", WebConfig)

    app = Application(name="memory-chat", config=config)
    app.add_modules(
        [
            MemoryModule.configure(
                MemoryConfig(default_backend="in_memory"),
                enable_consolidation=False,
            ),
            WebModule.configure(
                web_config=web_config,
                controllers=[ConciergeApiController, ChatPageController],
            ),
        ]
    )
    app.add_provider(ConciergeProvider())
    return app


__all__ = ["create_app"]
