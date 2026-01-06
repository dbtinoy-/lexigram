"""Streaming support for AgentExecutorImpl.

Provides the astream() method for streaming agent execution events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import uuid

from lexigram.contracts.ai.agents import AgentEvent, AgentEventType
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from lexigram.ai.agents.executor.executor import AgentExecutorImpl
    from lexigram.contracts.ai.agents import AgentProtocol


async def astream(
    self: AgentExecutorImpl,
    agent: AgentProtocol,
    message: str,
    session_id: str | None = None,
    user_id: str | None = None,
    **kwargs: Any,
):
    """Stream agent execution events.

    Yields AgentEvent objects as the agent executes, enabling
    real-time monitoring of thoughts, tool calls, and messages.

    Args:
        agent: The agent to execute.
        message: User's input message.
        session_id: Session ID for multi-turn memory.
        user_id: User ID for governance tracking.
        **kwargs: Additional parameters passed to the strategy.

    Yields:
        AgentEvent objects with type, data, and run_id.
    """
    run_id = str(uuid.uuid4())

    yield AgentEvent(
        type=AgentEventType.STARTED,
        data={
            "agent_name": agent.name,
            "session_id": session_id,
            "user_id": user_id,
            "message": message,
        },
        run_id=run_id,
    )

    governance_ok = await _check_governance(self, agent, user_id)
    if not governance_ok:
        yield AgentEvent(
            type=AgentEventType.ERROR,
            data={
                "error": "Governance denied request",
                "agent_name": agent.name,
            },
            run_id=run_id,
        )
        yield AgentEvent(
            type=AgentEventType.FINISHED,
            data={
                "agent_name": agent.name,
                "success": False,
                "error": "Governance denied",
            },
            run_id=run_id,
        )
        return

    guard_ok = await _check_guard_input(self, message, session_id, user_id)
    if not guard_ok:
        yield AgentEvent(
            type=AgentEventType.ERROR,
            data={
                "error": "Input blocked by guard pipeline",
                "agent_name": agent.name,
            },
            run_id=run_id,
        )
        yield AgentEvent(
            type=AgentEventType.FINISHED,
            data={
                "agent_name": agent.name,
                "success": False,
                "error": "Input blocked",
            },
            run_id=run_id,
        )
        return

    try:
        strategy = getattr(agent, "strategy", None)
        if strategy is None:
            from lexigram.ai.agents.strategies.react import ReActStrategy

            strategy = ReActStrategy()

        history = await _load_history(self, message, session_id)
        tools = list(agent.tools) if agent.tools else []
        await _merge_skills(self, tools)

        strategy_history = [{"role": m.role, "content": m.content} for m in history]

        result = await strategy.execute(
            message=message,
            tools=tools,
            history=strategy_history,
            llm=self._llm,  # type: ignore[arg-type]
            system_prompt=agent.system_prompt,
            temperature=getattr(agent, "temperature", 0.7),
            tool_registry=kwargs.get("tool_registry"),
            memory=getattr(agent, "memory", None),
            **kwargs,
        )

        if result.is_err():
            error = result.unwrap_err()
            yield AgentEvent(
                type=AgentEventType.ERROR,
                data={
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "agent_name": agent.name,
                },
                run_id=run_id,
            )
            yield AgentEvent(
                type=AgentEventType.FINISHED,
                data={
                    "agent_name": agent.name,
                    "success": False,
                    "error": str(error),
                },
                run_id=run_id,
            )
            return

        response = result.unwrap()

        await _check_guard_output(self, response.message, message, session_id, user_id)

        yield AgentEvent(
            type=AgentEventType.MESSAGE,
            data={
                "message": response.message,
                "agent_name": agent.name,
            },
            run_id=run_id,
        )

        yield AgentEvent(
            type=AgentEventType.FINISHED,
            data={
                "agent_name": agent.name,
                "success": True,
                "message": response.message,
                "steps": response.step_count,
                "tool_calls": response.tool_call_count,
                "total_tokens": response.total_tokens,
                "duration_ms": response.duration_ms,
            },
            run_id=run_id,
        )

    except Exception as e:
        logger.exception("astream_execution_failed", agent=agent.name)
        yield AgentEvent(
            type=AgentEventType.ERROR,
            data={
                "error": str(e),
                "error_type": type(e).__name__,
                "agent_name": agent.name,
            },
            run_id=run_id,
        )
        yield AgentEvent(
            type=AgentEventType.FINISHED,
            data={
                "agent_name": agent.name,
                "success": False,
                "error": str(e),
            },
            run_id=run_id,
        )


async def _check_governance(
    self: AgentExecutorImpl,
    agent: AgentProtocol,
    user_id: str | None,
) -> bool:
    """Check governance and emit events."""
    if not self._governance:
        return True

    try:
        model = getattr(self._llm, "model", "unknown")
        provider = getattr(self._llm, "provider", "unknown")
        allowed = await self._governance.check_request(
            model=model,
            provider=provider,
            user_id=user_id,
        )
        if not allowed:
            logger.warning(
                "agent_governance_denied",
                agent=agent.name,
                user_id=user_id,
            )
            return False
    except Exception as e:
        logger.warning("governance_check_failed", error=str(e))

    return True


async def _check_guard_input(
    self: AgentExecutorImpl,
    message: str,
    session_id: str | None,
    user_id: str | None,
) -> bool:
    """Check input guard pipeline."""
    if not self._guard_pipeline:
        return True

    try:
        guard_res = await self._guard_pipeline.check_input(
            content=message,
            metadata={"session_id": session_id, "user_id": user_id},
        )
        if not guard_res.is_ok():
            return False

        agg = guard_res.unwrap()
        blocked = bool(getattr(agg, "blocked", False))
        if blocked:
            logger.warning("input_blocked", session_id=session_id)
            return False
    except Exception as e:
        logger.warning("guard_input_check_failed", error=str(e))
    return True


async def _check_guard_output(
    self: AgentExecutorImpl,
    output: str,
    original_input: str,
    session_id: str | None,
    user_id: str | None,
) -> bool:
    """Check output guard pipeline."""
    if not self._guard_pipeline:
        return True

    try:
        guard_res = await self._guard_pipeline.check_output(
            content=output,
            original_input=original_input,
            metadata={"session_id": session_id, "user_id": user_id},
        )
        if not guard_res.is_ok():
            return False

        agg = guard_res.unwrap()
        blocked = bool(getattr(agg, "blocked", False))
        if blocked:
            logger.warning("output_blocked", session_id=session_id)
            return False
    except Exception as e:
        logger.warning("guard_output_check_failed", error=str(e))
    return True


async def _load_history(
    self: AgentExecutorImpl,
    message: str,
    session_id: str | None,
) -> list[Any]:
    """Load conversation history."""
    from lexigram.contracts.ai.llm import ChatMessage, Role

    history: list[ChatMessage] = []

    if self._working_memory:
        try:
            entries = await self._working_memory.assemble(
                query=message, token_budget=4096
            )
            history = [
                ChatMessage(role=Role(e.role), content=e.content) for e in entries
            ]
        except Exception as e:
            logger.warning("working_memory_assemble_failed", error=str(e))
    elif self._memory and session_id:
        try:
            if hasattr(self._memory, "get_messages"):
                msgs = await self._memory.get_messages()
                history = [
                    ChatMessage(role=Role(m.role), content=m.content) for m in msgs
                ]
        except Exception as e:
            logger.warning("memory_load_failed", error=str(e))

    return history


async def _merge_skills(
    self: AgentExecutorImpl,
    tools: list[Any],
) -> None:
    """Merge skills as additional tools."""
    if not self._skill_registry:
        return

    try:
        skill_schemas = self._skill_registry.get_schemas()
        tools.extend(skill_schemas)
    except Exception as e:
        logger.warning("skill_registry_merge_failed", error=str(e))
