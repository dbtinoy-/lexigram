"""MCP resource handler for the MCP server."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.mcp.exceptions import MCPError, MCPResourceError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


class ResourceHandler:
    """Handler for MCP resource-related methods.

    Handles resources/list, resources/read, and resources/templates/list
    methods by delegating to an MCPResourceProviderProtocol implementation.
    """

    def __init__(
        self,
        resource_provider: Any | None = None,
    ) -> None:
        """Initialize the resource handler.

        Args:
            resource_provider: Provider that handles resource operations.
        """
        self._provider = resource_provider

    async def list_resources(self) -> Result[dict[str, Any], MCPError]:
        """Handle resources/list method.

        Returns:
            ``Result`` containing resources list in MCP format.
        """
        if self._provider is None:
            return Ok({"resources": []})

        try:
            resources = await self._provider.list_resources()
            return Ok({"resources": resources})
        except (RuntimeError, TypeError, AttributeError, LookupError, OSError) as e:
            logger.error("mcp_list_resources_error", error=str(e))
            return Err(
                MCPResourceError(
                    message=f"Failed to list resources: {e!s}",
                    uri="resources/list",
                )
            )

    async def read_resource(self, uri: str) -> Result[dict[str, Any], MCPError]:
        """Handle resources/read method.

        Args:
            uri: URI of the resource to read.

        Returns:
            ``Result[dict[str, Any], MCPError]`` with MCP-formatted contents.
        """
        if self._provider is None:
            return Err(
                MCPResourceError(
                    message="No resource provider configured",
                    uri=uri,
                )
            )

        try:
            content = await self._provider.read_resource(uri)
            return Ok({"contents": [content]})
        except MCPResourceError as e:
            return Err(e)
        except (RuntimeError, TypeError, AttributeError, LookupError, OSError) as e:
            logger.error(
                "mcp_read_resource_error",
                uri=uri,
                error=str(e),
            )
            return Err(
                MCPResourceError(
                    message=f"Failed to read resource: {e!s}",
                    uri=uri,
                )
            )

    async def list_templates(self) -> Result[dict[str, Any], MCPError]:
        """Handle resources/templates/list method.

        Returns:
            ``Result`` containing URI templates in MCP format.
        """
        if self._provider is None:
            return Ok({"resourceTemplates": []})

        try:
            # Try to get templates if the provider supports it
            if hasattr(self._provider, "list_templates"):
                templates = await self._provider.list_templates()
                return Ok({"resourceTemplates": templates})
            return Ok({"resourceTemplates": []})
        except (RuntimeError, TypeError, AttributeError, LookupError, OSError) as e:
            logger.error("mcp_list_templates_error", error=str(e))
            return Err(
                MCPResourceError(
                    message=f"Failed to list resource templates: {e!s}",
                    uri="resources/templates/list",
                )
            )


__all__ = ["ResourceHandler"]
