"""MCP controller system — decorators, base class, and provider implementations."""

from __future__ import annotations

from lexigram.ai.mcp.controllers.base import MCPController
from lexigram.ai.mcp.controllers.decorators import prompt, resource, tool
from lexigram.ai.mcp.controllers.providers import (
    ControllerPromptProvider,
    ControllerResourceProvider,
    ControllerToolProvider,
    ModulePromptProvider,
    ModuleResourceProvider,
    ModuleToolProvider,
    ServiceToolProvider,
    _CombinedResourceProvider,
    _CombinedToolProvider,
)

__all__ = [
    "ControllerPromptProvider",
    "ControllerResourceProvider",
    "ControllerToolProvider",
    "MCPController",
    "ModulePromptProvider",
    "ModuleResourceProvider",
    "ModuleToolProvider",
    "ServiceToolProvider",
    "_CombinedResourceProvider",
    "_CombinedToolProvider",
    "prompt",
    "resource",
    "tool",
]
