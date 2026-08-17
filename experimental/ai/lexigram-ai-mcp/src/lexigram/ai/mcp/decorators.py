"""User-facing decorators for lexigram-ai-mcp.

Applied by application developers when defining MCP tools, resources,
and prompts for model context protocol servers.
"""

from __future__ import annotations

from lexigram.ai.mcp.controllers.decorators import (
    prompt as prompt,
)
from lexigram.ai.mcp.controllers.decorators import (
    resource as resource,
)
from lexigram.ai.mcp.controllers.decorators import (
    tool as tool,
)

__all__ = ["prompt", "resource", "tool"]
