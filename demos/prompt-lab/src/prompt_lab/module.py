"""Root module for the prompt-lab demo."""

from __future__ import annotations

import os

from lexigram.ai.prompt.module import PromptModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig
from prompt_lab.controllers.api import LabApiController
from prompt_lab.di.provider import LabProvider
from prompt_lab.services.ab_runner import ABRunner
from prompt_lab.ui.pages import LabPageController


@module()
class PromptLabModule(Module):
    """Prompt authoring lab with deterministic A/B scoring."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = (
            port if port is not None else int(os.environ.get("PROMPT_LAB_PORT", "8085"))
        )
        return DynamicModule(
            module=cls,
            imports=[
                PromptModule.configure(),
                WebModule.configure(
                    controllers=[LabApiController, LabPageController],
                    web_config=WebConfig(
                        server=ServerConfig(host="127.0.0.1", port=selected_port),
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[LabProvider],
            exports=[ABRunner],
        )


__all__ = ["PromptLabModule"]
