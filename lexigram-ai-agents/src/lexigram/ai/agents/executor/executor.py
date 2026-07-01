"""AgentExecutorImpl — runs agents with governance, memory, tracing, and metrics.

The executor is the bridge between the agent framework and the rest
of the Lexigram infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC
from typing import Any

from lexigram.ai.agents.exceptions import BudgetExceededError
from lexigram.ai.agents.executor.streaming import astream as _astream
from lexigram.ai.agents.observability import AgentMetrics, AgentTracer
from lexigram.ai.agents.strategies.guard_hook import (
    ToolObservationBlockedError,
    ToolObservationGuardError,
)
from lexigram.contracts.ai.agents import (
    AgentError,
    AgentExecutorProtocol,
    AgentProtocol,
    AgentResponse,
    MemoryProtocol,
)
from lexigram.contracts.ai.governance import AIGovernanceProtocol
from lexigram.contracts.ai.guards import GuardPipelineProtocol
from lexigram.contracts.ai.llm import (
    ChatMessage,
    CostEstimatorProtocol,
    LLMClientProtocol,
    Role,
)
from lexigram.contracts.ai.memory import WorkingMemoryProtocol
from lexigram.contracts.ai.session import SessionManagerProtocol
from lexigram.contracts.ai.skills import (
    SkillExecutorProtocol,
    SkillRegistryProtocol,
)
from lexigram.contracts.events.protocols import EventBusProtocol
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


@dataclass
class AgentObservability:
    """Composite for agent observability components.

    Groups metrics, tracing, and event publishing into a single injectable unit.
    """

    metrics: AgentMetrics | None = None
    tracer: AgentTracer | None = None
    event_bus: EventBusProtocol | None = None


@dataclass
class AgentSafetyInfra:
    """Composite for agent safety infrastructure.

    Groups governance and guard pipeline into a single injectable unit.
    """

    governance: AIGovernanceProtocol | None = None
    guard_pipeline: GuardPipelineProtocol | None = None


class AgentExecutorImpl(AgentExecutorProtocol):
    """Runs an agent with full infrastructure integration.

    Wraps agent strategy execution with:
    1. **Governance** — budget/rate limit checks
    2. **Memory** — conversation history load/save (legacy + working memory)
    3. **Metrics** — execution duration, tokens, tool calls
    4. **Tracing** — distributed spans per execution and tool call
    5. **Events** — domain events for agent lifecycle
    6. **Resilience** — circuit breakers on tool calls (via ToolRegistry)
    7. **Sessions** — stateful multi-turn conversation management
    8. **Skills** — composable skill execution and discovery

    Usage::

        executor = AgentExecutorImpl(llm=llm_client)
        result = await executor.run(
            agent=my_agent,
            message="Where is my order?",
            session_id="session-123",
        )
    """

    def __init__(
        self,
        llm: LLMClientProtocol | None = None,
        memory: MemoryProtocol | None = None,
        working_memory: WorkingMemoryProtocol | None = None,
        session_manager: SessionManagerProtocol | None = None,
        skill_executor: SkillExecutorProtocol | None = None,
        skill_registry: SkillRegistryProtocol | None = None,
        observability: AgentObservability | None = None,
        safety: AgentSafetyInfra | None = None,
        cost_estimator: CostEstimatorProtocol | None = None,
    ) -> None:
        """Initialize the agent executor.

        Args:
            llm: LLM client for agent reasoning.
            memory: Conversation memory for multi-turn sessions (legacy).
            working_memory: Working memory for context assembly.
            session_manager: Session manager for stateful conversations.
            skill_executor: Skill executor for running skills.
            skill_registry: Skill registry for discovering available skills.
            observability: Composite for metrics, tracer, and event bus.
                Defaults to isolated ``AgentMetrics`` and ``AgentTracer``.
            safety: Composite for governance and guard pipeline.
            cost_estimator: Estimates monetary cost of LLM usage for
                governance tracking. When omitted, cost is not tracked
                (no fabricated estimates).
        """
        self._llm = llm
        self._memory = memory
        self._working_memory = working_memory
        self._session_manager = session_manager
        self._skill_executor = skill_executor
        self._skill_registry = skill_registry
        self._cost_estimator = cost_estimator

        self._metrics = (
            observability.metrics
            if observability and observability.metrics
            else AgentMetrics()
        )
        self._tracer = (
            observability.tracer
            if observability and observability.tracer
            else AgentTracer()
        )
        self._event_bus = observability.event_bus if observability else None
        self._governance = safety.governance if safety else None
        self._guard_pipeline = safety.guard_pipeline if safety else None

    async def run(
        self,
        agent: AgentProtocol,
        message: str,
        session_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> Result[AgentResponse, AgentError]:
        """Execute an agent with full infrastructure integration.

        Args:
            agent: The agent to execute.
            message: User's input message.
            session_id: Session ID for multi-turn memory.
            user_id: User ID for governance tracking.
            **kwargs: Additional parameters passed to the strategy.

        Returns:
            ``Ok(AgentResponse)`` on success,
            ``Err(AgentError)`` on failure.
        """
        logger.info(
            "agent_execution_start",
            agent=agent.name,
            session_id=session_id,
            user_id=user_id,
            message_length=len(message),
        )

        # Publish start event
        await self._publish_event(
            "AgentExecutionStarted",
            {
                "agent_name": agent.name,
                "session_id": session_id,
                "user_id": user_id,
            },
        )

        # 1. Governance check
        if self._governance:
            model = getattr(self._llm, "model", "unknown")
            provider = getattr(self._llm, "provider", "unknown")
            try:
                allowed = await self._governance.check_request(
                    model=model,
                    provider=provider,
                    user_id=user_id,
                )
                if not allowed:
                    self._metrics.record_governance_denied(agent.name)
                    logger.warning(
                        "agent_governance_denied",
                        agent=agent.name,
                        user_id=user_id,
                    )
                    await self._publish_event(
                        "AgentExecutionFailed",
                        {
                            "agent_name": agent.name,
                            "error": "Governance denied",
                            "error_type": "BudgetExceededError",
                        },
                    )
                    return Err(
                        BudgetExceededError(
                            "Agent request denied by governance policy",
                        )
                    )
            except (RuntimeError, OSError) as e:
                logger.warning("governance_check_failed", error=str(e))

        # Agent-level pipeline (AgentBuilder.with_guard_pipeline) wins over the
        # DI-provided one; the DI pipeline remains the standard default.
        guard_pipeline = getattr(agent, "guard_pipeline", None) or self._guard_pipeline

        # 1.5 Guard check for input
        if guard_pipeline:
            try:
                guard_res = await guard_pipeline.check_input(
                    content=message,
                    metadata={"session_id": session_id, "user_id": user_id},
                )
                if not guard_res.is_ok():
                    return Err(
                        AgentError(f"Guard pipeline failure: {guard_res.unwrap_err()}")
                    )

                agg = guard_res.unwrap()
                blocked = bool(getattr(agg, "blocked", False))
                if blocked:
                    blocking_result = getattr(agg, "blocking_result", None)
                    reason = (
                        getattr(blocking_result, "reason", None)
                        or "Input blocked by security guards"
                    )
                    return Err(
                        AgentError(f"Input blocked by security guards: {reason}")
                    )

                message = str(getattr(agg, "final_content", message))
            except (RuntimeError, OSError) as e:
                logger.exception("input_guard_evaluation_failed", agent=agent.name)
                return Err(AgentError(f"Guard evaluation failed: {e}", cause=e))

        # 2a. Resume or create session
        session_state = None
        if self._session_manager and session_id:
            try:
                session_state = await self._session_manager.resume(session_id)
                if session_state is None and user_id:
                    session_state = await self._session_manager.create(
                        user_id=user_id,
                        metadata={"agent": agent.name},
                    )
                    session_id = session_state.session_id
                logger.debug(
                    "session_loaded",
                    session_id=session_id,
                    turns=session_state.turn_count if session_state else 0,
                )
            except (RuntimeError, TypeError, AttributeError, LookupError) as e:
                logger.warning("session_load_failed", error=str(e))

        # 2b. Assemble context via working memory (preferred) or legacy memory
        history: list[ChatMessage] = []
        if self._working_memory:
            try:
                entries = await self._working_memory.assemble(
                    query=message, token_budget=4096
                )
                history = [
                    ChatMessage(role=Role(e.role), content=e.content) for e in entries
                ]
            except (RuntimeError, TypeError, AttributeError, LookupError) as e:
                logger.warning("working_memory_assemble_failed", error=str(e))
        elif self._memory and session_id:
            try:
                if hasattr(self._memory, "get_messages"):
                    msgs = await self._memory.get_messages()
                    history = [
                        ChatMessage(role=Role(m.role), content=m.content) for m in msgs
                    ]
            except (RuntimeError, TypeError, AttributeError, LookupError) as e:
                logger.warning("memory_load_failed", error=str(e))

        # 2c. Merge skills as additional tools
        tools: list[Any] = list(agent.tools) if agent.tools else []
        if self._skill_registry:
            try:
                skill_schemas = self._skill_registry.get_schemas()
                tools.extend(skill_schemas)
            except (RuntimeError, TypeError, AttributeError, LookupError) as e:
                logger.warning("skill_registry_merge_failed", error=str(e))

        # 3. Execute strategy with tracing
        strategy = getattr(agent, "strategy", None)
        if strategy is None:
            from lexigram.ai.agents.strategies.react import ReActStrategy

            strategy = ReActStrategy()

        if self._llm is None:
            logger.error("agent_executor_missing_llm", agent=agent.name)
            await self._publish_event(
                "AgentExecutionFailed",
                {
                    "agent_name": agent.name,
                    "error": "No LLM client configured",
                    "error_type": "ConfigurationError",
                },
            )
            return Err(AgentError("Agent executor has no LLM client configured"))

        try:
            async with self._tracer.trace_execution(
                agent.name,
                message,
                session_id,
            ) as span:
                strategy_history = [
                    {"role": m.role, "content": m.content} for m in history
                ]

                result = await strategy.execute(
                    message=message,
                    tools=tools,
                    history=strategy_history,
                    llm=self._llm,
                    system_prompt=agent.system_prompt,
                    temperature=getattr(agent, "temperature", 0.7),
                    tool_registry=kwargs.get("tool_registry"),
                    memory=getattr(agent, "memory", None),
                    guard_pipeline=guard_pipeline,
                    **kwargs,
                )

                if span and hasattr(result, "is_ok"):
                    if result.is_ok():
                        response = result.unwrap()
                        if hasattr(span, "set_attribute"):
                            span.set_attribute("agent.steps", response.step_count)
                            span.set_attribute("agent.tokens", response.total_tokens)
                            span.set_attribute(
                                "agent.tool_calls", response.tool_call_count
                            )

        except (ToolObservationBlockedError, ToolObservationGuardError) as e:
            logger.warning(
                "agent.guard_blocked_observation",
                agent=agent.name,
                error=str(e),
            )
            self._metrics.record_error(agent.name, type(e).__name__)
            await self._publish_event(
                "AgentExecutionFailed",
                {
                    "agent_name": agent.name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return Err(AgentError(f"Tool observation blocked by guards: {e}", cause=e))

        except (RuntimeError, OSError) as e:
            logger.exception("strategy_execution_failed", agent=agent.name)
            self._metrics.record_error(agent.name, type(e).__name__)
            await self._publish_event(
                "AgentExecutionFailed",
                {
                    "agent_name": agent.name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return Err(AgentError(f"Strategy failed: {e}", cause=e))

        if not result.is_ok():
            error = result.unwrap_err()
            error_type = type(error).__name__
            self._metrics.record_error(agent.name, error_type)
            await self._publish_event(
                "AgentExecutionFailed",
                {
                    "agent_name": agent.name,
                    "error": str(error),
                    "error_type": error_type,
                },
            )
            if isinstance(error, AgentError):
                return Err(error)
            return Err(AgentError(str(error), cause=error))

        response = result.unwrap()

        # 3.5 Guard check for output
        if guard_pipeline:
            try:
                out_guard_res = await guard_pipeline.check_output(
                    content=response.message,
                    original_input=message,
                    metadata={"session_id": session_id, "user_id": user_id},
                )
                if not out_guard_res.is_ok():
                    return Err(
                        AgentError(
                            f"Guard pipeline failure: {out_guard_res.unwrap_err()}"
                        )
                    )

                agg = out_guard_res.unwrap()
                blocked = bool(getattr(agg, "blocked", False))
                if blocked:
                    blocking_result = getattr(agg, "blocking_result", None)
                    reason = (
                        getattr(blocking_result, "reason", None)
                        or "Output blocked by security guards"
                    )
                    return Err(
                        AgentError(f"Output blocked by security guards: {reason}")
                    )

                response = replace(
                    response,
                    message=str(getattr(agg, "final_content", response.message)),
                )
            except (RuntimeError, OSError) as e:
                logger.exception("output_guard_evaluation_failed", agent=agent.name)
                return Err(AgentError(f"Guard evaluation failed: {e}", cause=e))

        # 4. Record metrics
        self._metrics.record_execution(agent.name, response)
        for tc in response.tool_calls:
            self._metrics.record_tool_call(agent.name, tc)

        # 5. Save to memory (working memory, session, and/or legacy)
        if self._working_memory:
            try:
                from datetime import datetime

                from lexigram.contracts.ai.memory import MemoryEntry

                user_entry = MemoryEntry(
                    id=f"{session_id or 'no-session'}-user-{response.step_count}",
                    content=message,
                    role="user",
                    timestamp=datetime.now(UTC),
                )
                assistant_entry = MemoryEntry(
                    id=f"{session_id or 'no-session'}-assistant-{response.step_count}",
                    content=response.message,
                    role="assistant",
                    timestamp=datetime.now(UTC),
                )
                await self._working_memory.add(user_entry)
                await self._working_memory.add(assistant_entry)
            except (RuntimeError, TypeError, AttributeError, LookupError) as e:
                logger.warning("working_memory_save_failed", error=str(e))

        if self._session_manager and session_id:
            try:
                from datetime import datetime

                from lexigram.contracts.ai.session import SessionTurn

                user_turn = SessionTurn(
                    turn_id=f"{session_id}-user-{response.step_count}",
                    role="user",
                    content=message,
                    timestamp=datetime.now(UTC),
                )
                assistant_turn = SessionTurn(
                    turn_id=f"{session_id}-assistant-{response.step_count}",
                    role="assistant",
                    content=response.message,
                    timestamp=datetime.now(UTC),
                    tokens_used=response.total_tokens,
                    tool_calls=[
                        {"name": tc.tool_name, "result": tc.result}
                        for tc in response.tool_calls
                    ],
                )
                await self._session_manager.add_turn(session_id, user_turn)
                await self._session_manager.add_turn(session_id, assistant_turn)
            except (RuntimeError, TypeError, AttributeError, LookupError) as e:
                logger.warning("session_turn_save_failed", error=str(e))

        if self._memory and session_id:
            try:
                if hasattr(self._memory, "add"):
                    await self._memory.add("user", message)
                    await self._memory.add("assistant", response.message)
                elif hasattr(self._memory, "add_message"):
                    await self._memory.add_message(
                        ChatMessage(role=Role.USER, content=message),
                    )
                    await self._memory.add_message(
                        ChatMessage(role=Role.ASSISTANT, content=response.message),
                    )
            except (RuntimeError, TypeError, AttributeError, LookupError) as e:
                logger.warning("memory_save_failed", error=str(e))

        # 6. Track cost (only when a real estimator is configured)
        if self._governance and self._cost_estimator and response.total_tokens > 0:
            try:
                model = getattr(self._llm, "model", "unknown")
                estimated_cost = self._cost_estimator.estimate_cost(
                    model=model,
                    total_tokens=response.total_tokens,
                    provider=getattr(self._llm, "provider", None),
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                )
                await self._governance.track_cost(
                    cost=estimated_cost,
                    model=model,
                    user_id=user_id,
                )
                response = replace(response, total_cost=estimated_cost)
            except (RuntimeError, OSError) as e:
                logger.warning("cost_tracking_failed", error=str(e))

        response = replace(response, session_id=session_id)

        # 7. Publish completion event
        await self._publish_event(
            "AgentExecutionCompleted",
            {
                "agent_name": agent.name,
                "session_id": session_id,
                "steps": response.step_count,
                "tool_calls": response.tool_call_count,
                "total_tokens": response.total_tokens,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_cost": response.total_cost,
                "duration_ms": response.duration_ms,
            },
        )

        logger.info(
            "agent_execution_complete",
            agent=agent.name,
            steps=response.step_count,
            tool_calls=response.tool_call_count,
            tokens=response.total_tokens,
            duration_ms=round(response.duration_ms, 2),
        )

        return Ok(response)

    async def astream(
        self,
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
        async for event in _astream(
            self,
            agent,
            message,
            session_id,
            user_id,
            **kwargs,
        ):
            yield event

    async def _publish_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Publish an agent domain event if EventBusProtocol is available."""
        if not self._event_bus:
            return

        try:
            from lexigram.ai.agents import events as agent_events

            event_cls = getattr(agent_events, event_type, None)
            if event_cls:
                event_obj = event_cls(**data)
                await self._event_bus.publish(event_obj)
        except (ImportError, AttributeError):
            pass
        except (RuntimeError, OSError, ConnectionError, TypeError) as e:
            logger.debug("event_publish_failed", event_type=event_type, error=str(e))
