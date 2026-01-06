"""MCP prompt handler for the MCP server."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.mcp.exceptions import MCPError, MCPPromptError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


class PromptHandler:
    """Handler for MCP prompt-related methods.

    Handles prompts/list and prompts/get methods by delegating to an
    MCPPromptProviderProtocol implementation.
    """

    def __init__(
        self,
        prompt_provider: Any | None = None,
    ) -> None:
        """Initialize the prompt handler.

        Args:
            prompt_provider: Provider that handles prompt operations.
        """
        self._provider = prompt_provider

    async def list_prompts(self) -> Result[dict[str, Any], MCPError]:
        """Handle prompts/list method.

        Returns:
            ``Result`` containing prompts list in MCP format.
        """
        if self._provider is None:
            return Ok({"prompts": []})

        try:
            prompts = await self._provider.list_prompts()
            return Ok({"prompts": prompts})
        except (RuntimeError, TypeError, AttributeError, LookupError, OSError) as e:
            logger.error("mcp_list_prompts_error", error=str(e))
            return Err(
                MCPPromptError(
                    message=f"Failed to list prompts: {e!s}",
                    prompt_name="prompts/list",
                )
            )

    async def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Result[dict[str, Any], MCPError]:
        """Handle prompts/get method.

        Args:
            name: Name of the prompt to get.
            arguments: Arguments to fill in the prompt template.

        Returns:
            ``Result[dict[str, Any], MCPError]`` with prompt payload.
        """
        if self._provider is None:
            return Err(
                MCPPromptError(
                    message="No prompt provider configured",
                    prompt_name=name,
                )
            )

        if arguments is None:
            arguments = {}

        try:
            prompt = await self._provider.get_prompt(name, arguments)
            return Ok(prompt)
        except MCPPromptError as e:
            return Err(e)
        except (RuntimeError, TypeError, AttributeError, LookupError, OSError) as e:
            logger.error(
                "mcp_get_prompt_error",
                prompt=name,
                error=str(e),
            )
            return Err(
                MCPPromptError(
                    message=f"Failed to get prompt: {e!s}",
                    prompt_name=name,
                )
            )


__all__ = ["PromptHandler"]
