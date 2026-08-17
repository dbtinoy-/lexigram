"""Discovery utilities for auto-registration of skills from modules and MCP."""

from __future__ import annotations

from lexigram.ai.skills.discovery.mcp_bridge import MCPSkillBridge
from lexigram.ai.skills.discovery.module_scanner import ModuleScanner
from lexigram.ai.skills.discovery.skill_loader import SkillLoader
from lexigram.ai.skills.discovery.skill_source_scanner import SkillSourceScanner

__all__ = [
    "MCPSkillBridge",
    "ModuleScanner",
    "SkillLoader",
    "SkillSourceScanner",
]
