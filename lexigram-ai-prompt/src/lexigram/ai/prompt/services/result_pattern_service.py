"""Prompt service using Result pattern."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import AIError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


class PromptServiceWithResultPattern:
    """Prompt service using Result pattern."""

    async def render(self, template_name: str, variables: dict) -> Result[str, AIError]:
        """Render a prompt template."""
        try:
            if not template_name:
                return Err(AIError("Template name cannot be empty"))
            prompt = f"{template_name}: {variables}"
            logger.info("prompt_rendered", template=template_name)
            return Ok(prompt)
        except Exception as e:  # noqa: BLE001  # prompt rendering can raise any exception; surfaced as Err
            logger.error("prompt_render_failed: %s", e)
            return Err(AIError(f"Prompt rendering failed: {e}"))


__all__ = ["PromptServiceWithResultPattern"]
