"""MCP exceptions - re-exported from contracts.

This module re-exports the MCP error hierarchy from lexigram-contracts
for convenient access within the lexigram-mcp package.

Extensions that need to add package-specific exceptions can extend
the base classes from lexigram.contracts.mcp.exceptions.
"""

from __future__ import annotations

from lexigram.contracts.mcp.exceptions import (
    MCPError,
    MCPInitializationError,
    MCPMethodNotFoundError,
    MCPPromptError,
    MCPProtocolError,
    MCPResourceError,
    MCPToolCallError,
    MCPTransportError,
)

__all__ = [
    "MCPError",
    "MCPInitializationError",
    "MCPMethodNotFoundError",
    "MCPPromptError",
    "MCPProtocolError",
    "MCPResourceError",
    "MCPToolCallError",
    "MCPTransportError",
]
