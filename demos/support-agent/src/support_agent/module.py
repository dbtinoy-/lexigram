"""Root module for the support-agent demo."""

from __future__ import annotations

import os

from lexigram.ai.agents import AgentConfig, AgentsModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig
from support_agent.api import AgentApiController
from support_agent.di.provider import AgentSupportProvider
from support_agent.services.support_service import SupportAgent
from support_agent.ui.pages import ConsolePageController


@module()
class SupportAgentModule(Module):
    """Support-desk ReAct agent with a scripted LLM and web console."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = (
            port
            if port is not None
            else int(os.environ.get("SUPPORT_AGENT_PORT", "8082"))
        )
        return DynamicModule(
            module=cls,
            imports=[
                AgentsModule.configure(AgentConfig(max_iterations=5)),
                WebModule.configure(
                    controllers=[AgentApiController, ConsolePageController],
                    web_config=WebConfig(
                        server=ServerConfig(host="127.0.0.1", port=selected_port),
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[AgentSupportProvider],
            exports=[SupportAgent],
        )


__all__ = ["SupportAgentModule"]
