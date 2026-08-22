"""Agent construction and the API-facing facade."""

from __future__ import annotations

from support_agent.tools import SUPPORT_TOOLS

from lexigram.ai.agents import AgentBuilder
from lexigram.contracts.ai.agents import (
    AgentError,
    AgentExecutorProtocol,
    AgentProtocol,
    AgentResponse,
)
from lexigram.logging import get_logger
from lexigram.result import Result

logger = get_logger(__name__)


SYSTEM_PROMPT = (
    "You are support-agent, a customer support assistant for an online "
    "store. Use the provided tools to look up orders, compute refunds, "
    "and search the knowledge base before answering. Be precise."
)


def build_support_agent() -> AgentProtocol:
    """Assemble the support-desk agent with its three tools."""
    return (
        AgentBuilder("support-agent")
        .with_system_prompt(SYSTEM_PROMPT)
        .with_tools(*SUPPORT_TOOLS)
        .with_strategy("react")
        .build()
    )


class SupportAgent:
    """Concrete facade: one question in, one traced response out."""

    def __init__(self, executor: AgentExecutorProtocol, agent: AgentProtocol) -> None:
        self._executor = executor
        self._agent = agent
        self.last_response: AgentResponse | None = None

    async def ask(self, question: str) -> Result[AgentResponse, AgentError]:
        """Run one ReAct turn against the scripted LLM."""
        result: Result[AgentResponse, AgentError] = await self._executor.run(
            agent=self._agent,
            message=question,
        )
        if result.is_ok():
            self.last_response = result.unwrap()
            logger.info(
                "agent_ask_complete",
                tool_calls=self.last_response.tool_call_count,
                tokens=self.last_response.total_tokens,
            )
        return result
