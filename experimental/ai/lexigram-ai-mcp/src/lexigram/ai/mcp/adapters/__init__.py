"""MCP adapters for integrating with other Lexigram components."""

from __future__ import annotations

from lexigram.ai.mcp.adapters.skill_adapter import SkillToolAdapter
from lexigram.ai.mcp.adapters.tool_adapter import ToolRegistryAdapter

__all__ = ["SkillToolAdapter", "ToolRegistryAdapter"]
