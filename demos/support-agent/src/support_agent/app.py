"""Application composition root for the support-agent demo."""

from __future__ import annotations

from lexigram.ai.agents import AgentConfig, AgentsModule
from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from support_agent.config import load_lex_config
from support_agent.controllers.api import AgentApiController
from support_agent.di.provider import AgentSupportProvider
from support_agent.ui.pages import ConsolePageController


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) support-agent application."""
    config = config or load_lex_config()
    web_config = config.get_section("web", WebConfig)

    app = Application(name="support-agent", config=config)
    app.add_modules(
        [
            AgentsModule.configure(AgentConfig(max_iterations=5)),
            WebModule.configure(
                web_config=web_config,
                controllers=[AgentApiController, ConsolePageController],
            ),
        ]
    )
    app.add_provider(AgentSupportProvider())
    return app


__all__ = ["create_app"]
