"""MCPSkillBridge — bidirectional bridge between MCP tools and Lexigram skills."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.skills.registry import SkillRegistry

logger = get_logger(__name__)


class MCPSkillBridge:
    """Import MCP tools as Lexigram skills and export skills as MCP tools.

    This bridge allows a skill registry to expose its skills to MCP-aware
    callers and consume MCP tools as if they were first-class skills.

    Note:
        The MCP integration uses :mod:`lexigram.ai.mcp` when available.
        This class is a stub that gracefully degrades when the MCP package
        is not installed.
    """

    def __init__(self, registry: SkillRegistry) -> None:
        """Initialise the bridge with the backing registry.

        Args:
            registry: The skill registry to import into / export from.
        """
        self._registry = registry

    async def import_from_mcp(self, mcp_client: Any) -> int:
        """Register all tools exposed by an MCP client as skills.

        Args:
            mcp_client: An object implementing :class:`MCPClientProtocol`
                (from ``lexigram.ai.mcp``).

        Returns:
            Number of tools successfully imported as skills.
        """
        try:
            tools = await mcp_client.list_tools()
        except (
            Exception
        ) as exc:  # MCP transport can raise any exception; logged and re-raised
            logger.error("mcp_bridge_list_tools_error", error=str(exc))
            raise

        imported = 0
        for tool in tools:
            try:
                self._registry.register_tool(tool)
                imported += 1
                logger.debug("mcp_bridge_imported_tool", name=tool.name)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "mcp_bridge_import_error", name=tool.name, error=str(exc)
                )

        logger.info("mcp_bridge_import_complete", imported=imported)
        return imported

    def get_mcp_tool_definitions(self) -> list[dict[str, Any]]:
        """Export all registered skills as MCP tool definitions.

        Returns:
            List of dicts following the MCP tool definition schema.
        """
        schemas = self._registry.get_schemas()
        return [
            {
                "name": s["function"]["name"],
                "description": s["function"]["description"],
                "inputSchema": s["function"]["parameters"],
            }
            for s in schemas
        ]
