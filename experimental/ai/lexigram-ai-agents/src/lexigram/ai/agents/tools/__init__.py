"""Tools module for agent tools."""
from __future__ import annotations

from lexigram.ai.agents.tools.base import AbstractTool
from lexigram.ai.agents.tools.decorator import tool
from lexigram.ai.agents.tools.registry import ToolRegistryImpl
from lexigram.ai.agents.tools.schema import generate_json_schema

ToolBase = AbstractTool

__all__ = [
    "AbstractTool",
    "ToolBase",
    "ToolRegistryImpl",
    "generate_json_schema",
    "tool",
]
