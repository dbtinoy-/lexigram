"""Re-export MCP protocols for consumer convenience.

Consumers use these contracts to depend on MCP abstractions without
importing the full lexigram-ai-mcp implementation.
"""

from __future__ import annotations

from lexigram.contracts.mcp.protocols import (
    MCPPromptHandlerProtocol as MCPPromptHandlerProtocol,
)
from lexigram.contracts.mcp.protocols import (
    MCPPromptProviderProtocol as MCPPromptProviderProtocol,
)
from lexigram.contracts.mcp.protocols import (
    MCPResourceHandlerProtocol as MCPResourceHandlerProtocol,
)
from lexigram.contracts.mcp.protocols import (
    MCPResourceProviderProtocol as MCPResourceProviderProtocol,
)
from lexigram.contracts.mcp.protocols import (
    MCPServerProtocol as MCPServerProtocol,
)
from lexigram.contracts.mcp.protocols import (
    MCPToolHandlerProtocol as MCPToolHandlerProtocol,
)
from lexigram.contracts.mcp.protocols import (
    MCPToolProviderProtocol as MCPToolProviderProtocol,
)
from lexigram.contracts.mcp.protocols import (
    MCPTransportProtocol as MCPTransportProtocol,
)

__all__ = [
    "MCPPromptHandlerProtocol",
    "MCPPromptProviderProtocol",
    "MCPResourceHandlerProtocol",
    "MCPResourceProviderProtocol",
    "MCPServerProtocol",
    "MCPToolHandlerProtocol",
    "MCPToolProviderProtocol",
    "MCPTransportProtocol",
]
