"""Agent executor service using Result pattern."""

from __future__ import annotations

from lexigram.contracts.ai.agents import AgentError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


class AgentExecutorWithResultPattern:
    """Agent executor using Result pattern."""

    async def execute(
        self, agent_name: str, task: str, tools: list | None = None
    ) -> Result[dict, AgentError]:
        """Execute an agent."""
        try:
            if not agent_name:
                return Err(AgentError("Agent name cannot be empty"))
            if not task:
                return Err(AgentError("Task cannot be empty"))
            result = {"agent": agent_name, "task": task, "result": "completed"}
            logger.info("agent_executed", agent=agent_name, tools=len(tools or []))
            return Ok(result)
        except (RuntimeError, ValueError, TypeError, AttributeError) as e:
            logger.error("agent_execution_failed: %s", e)
            return Err(AgentError(f"Agent execution failed: {e}"))


__all__ = ["AgentExecutorWithResultPattern"]
