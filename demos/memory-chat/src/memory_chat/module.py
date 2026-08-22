"""Root module for the memory-chat demo."""

from __future__ import annotations

import os

from lexigram.ai.memory import MemoryConfig, MemoryModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig

from memory_chat.chat_service import ConciergeService
from memory_chat.controllers.api import ConciergeApiController
from memory_chat.di.provider import ConciergeProvider
from memory_chat.ui.pages import ChatPageController


@module()
class MemoryChatModule(Module):
    """Conversational memory concierge with a two-owner web console."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = port if port is not None else int(
            os.environ.get("MEMORY_CHAT_PORT", "8083")
        )
        return DynamicModule(
            module=cls,
            imports=[
                MemoryModule.configure(
                    MemoryConfig(default_backend="in_memory"),
                    enable_consolidation=False,
                ),
                WebModule.configure(
                    controllers=[ConciergeApiController, ChatPageController],
                    web_config=WebConfig(
                        server=ServerConfig(host="127.0.0.1", port=selected_port),
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[ConciergeProvider],
            exports=[ConciergeService],
        )


__all__ = ["MemoryChatModule"]
