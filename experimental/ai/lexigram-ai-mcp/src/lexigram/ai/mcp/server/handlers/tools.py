"""MCP tool handler for the MCP server."""

from __future__ import annotations

from typing import Any

from lexigram.ai.mcp.types import MCPToolResult
from lexigram.contracts.mcp.exceptions import MCPError, MCPToolCallError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


class ToolHandler:
    """Handler for MCP tool-related methods.

    Handles tools/list and tools/call methods by delegating to a
    MCPToolProviderProtocol implementation.

    All handler methods return ``Result`` so callers can handle expected
    failures without raising exceptions.
    """

    def __init__(
        self,
        tool_provider: Any | None = None,
    ) -> None:
        """Initialize the tool handler.

        Args:
            tool_provider: Provider that handles tool listing and execution.
        """
        self._provider = tool_provider

    async def list_tools(self) -> Result[dict[str, Any], MCPError]:
        """Handle tools/list method.

        Returns:
            ``Result`` containing tools list in MCP format.
        """
        if self._provider is None:
            return Ok({"tools": []})

        try:
            tools = await self._provider.list_tools()
            return Ok({"tools": tools})
        except (RuntimeError, TypeError, AttributeError, LookupError, OSError) as e:
            logger.error("mcp_list_tools_error", error=str(e))
            return Err(
                MCPToolCallError(
                    message=f"Failed to list tools: {e!s}",
                    tool_name="tools/list",
                )
            )

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Result[dict[str, Any], MCPError]:
        """Handle tools/call method.

        Returns a ``Result`` — ``Ok`` wraps the serialized MCP tool result dict;
        ``Err`` wraps an :class:`~lexigram.contracts.mcp.exceptions.MCPToolCallError`
        describing what went wrong.

        Args:
            name: Name of the tool to call.
            arguments: Arguments to pass to the tool.

        Returns:
            ``Result[dict[str, Any], MCPError]`` — never raises expected errors.
        """
        if self._provider is None:
            return Err(
                MCPToolCallError(
                    message="No tool provider configured",
                    tool_name=name,
                )
            )

        if arguments is None:
            arguments = {}

        try:
            result = await self._provider.call_tool(name, arguments)
        except MCPToolCallError as e:
            logger.error("mcp_tool_call_error", tool=name, error=str(e))
            return Err(e)
        except (ValueError, TypeError, KeyError) as e:
            logger.error("mcp_tool_call_invalid_args", tool=name, error=str(e))
            return Err(
                MCPToolCallError(
                    message=f"Invalid arguments for tool '{name}': {e}",
                    tool_name=name,
                )
            )
        except (AttributeError, LookupError, OSError, RuntimeError) as e:
            logger.error("mcp_tool_call_error", tool=name, error=str(e))
            return Err(
                MCPToolCallError(
                    message=f"Tool call failed: {e!s}",
                    tool_name=name,
                )
            )

        # Normalise result to MCP wire format
        if isinstance(result, MCPToolResult):
            return Ok(result.to_dict())
        return Ok(MCPToolResult.text(str(result)).to_dict())


__all__ = ["ToolHandler"]
