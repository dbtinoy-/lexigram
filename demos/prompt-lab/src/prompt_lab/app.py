"""Application composition root for the prompt-lab demo."""

from __future__ import annotations

from lexigram.ai.prompt.module import PromptModule
from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from prompt_lab.config import load_lex_config
from prompt_lab.controllers.api import LabApiController
from prompt_lab.di.provider import LabProvider
from prompt_lab.ui.pages import LabPageController


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) prompt-lab application."""
    config = config or load_lex_config()
    web_config = config.get_section("web", WebConfig)

    app = Application(name="prompt-lab", config=config)
    app.add_modules(
        [
            PromptModule.configure(),
            WebModule.configure(
                web_config=web_config,
                controllers=[LabApiController, LabPageController],
            ),
        ]
    )
    app.add_provider(LabProvider())
    return app


__all__ = ["create_app"]
