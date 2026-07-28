"""Built-in MCP resource providers."""

from __future__ import annotations

from lexigram.ai.mcp.resources.config import ConfigResourceProvider
from lexigram.ai.mcp.resources.database import DatabaseResourceProvider
from lexigram.ai.mcp.resources.search import SearchResourceProvider

__all__ = [
    "ConfigResourceProvider",
    "DatabaseResourceProvider",
    "SearchResourceProvider",
]
