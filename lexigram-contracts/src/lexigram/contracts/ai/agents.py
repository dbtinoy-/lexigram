"""Agent contracts for the Lexigram framework.

Exceptions, types, and protocols for agents, tools, and strategies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from lexigram.contracts.exceptions.base import LexigramError

if TYPE_CHECKING:
    from lexigram.contracts.core.module import CompiledModuleGraphProtocol
    from lexigram.contracts.core.result import Result


class AgentEventType(str, Enum):
    """Event types emitted during agent streaming execution."""

    STARTED = "started"
    """Agent execution has started."""

    THOUGHT = "thought"
    """Agent emitted a thought/reasoning step."""

    TOOL_START = "tool_start"
    """Tool execution is about to start."""

    TOOL_END = "tool_end"
    """Tool execution has completed."""

    MESSAGE = "message"
    """Agent emitted a message (intermediate or final)."""

    ERROR = "error"
    """An error occurred during execution."""

    FINISHED = "finished"
    """Agent execution has finished."""


@dataclass(frozen=True)
class AgentEvent:
    """Event emitted during agent streaming execution.

    Attributes:
        type: The type of event.
        data: Event payload data.
        run_id: Unique identifier for this execution run.
    """

    type: AgentEventType
    """The type of event."""

    data: dict[str, Any]
    """Event payload data."""

    run_id: str
    """Unique identifier for this execution run."""


# ---------------------------------------------------------------------------
# Section 1: Exceptions
# ---------------------------------------------------------------------------


class AgentError(LexigramError):
    """Base exception for all agent errors."""

    _code = "LEX_ERR_AGT_001"

    def __init__(self, message: str = "Agent error", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            **kwargs,
        )


class ToolError(AgentError):
    """Base exception for tool errors."""

    _code = "LEX_ERR_AGT_002"

    def __init__(self, message: str = "Tool error", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            **kwargs,
        )


class StrategyError(AgentError):
    """Reasoning strategy failed.

    Raised when the agent's strategy encounters an error
    during reasoning (LLM failure, invalid response, etc.).
    """

    _code = "LEX_ERR_AGT_003"

    def __init__(
        self,
        message: str = "Strategy execution failed",
        *,
        strategy_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if strategy_name:
            details["strategy"] = strategy_name
        super().__init__(
            message=message,
            details=details,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Section 2: Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentResponse:
    """Complete response from an agent execution.

    Contains the final message, the full reasoning trace (steps),
    all tool calls made, token usage, cost, and timing metadata.

    Note: ToolCall and ReasoningStep are defined in lexigram-ai-agents
    and imported here for use in this type's field annotations.
    """

    message: str
    """The agent's final response to the user."""

    steps: list[Any] = field(default_factory=list)
    """Full reasoning trace — every thought, action, and observation."""

    tool_calls: list[Any] = field(default_factory=list)
    """All tool invocations made during this execution."""

    total_tokens: int = 0
    """Total LLM tokens consumed (prompt + completion)."""

    total_cost: float = 0.0
    """Estimated cost in USD."""

    duration_ms: float = 0.0
    """Total execution time in milliseconds."""

    session_id: str | None = None
    """Session identifier for multi-turn conversations."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata (model name, strategy used, etc.)."""

    @property
    def tool_call_count(self) -> int:
        """Number of tool calls made."""
        return len(self.tool_calls)

    @property
    def step_count(self) -> int:
        """Number of reasoning steps taken."""
        return len(self.steps)

    @property
    def successful_tool_calls(self) -> list[Any]:
        """Tool calls that completed without error."""
        return [tc for tc in self.tool_calls if getattr(tc, "succeeded", True)]

    @property
    def failed_tool_calls(self) -> list[Any]:
        """Tool calls that failed."""
        return [tc for tc in self.tool_calls if not getattr(tc, "succeeded", True)]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "message": self.message,
            "steps": len(self.steps),
            "tool_calls": len(self.tool_calls),
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "duration_ms": self.duration_ms,
            "session_id": self.session_id,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ToolDefinition:
    """Schema for a tool."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    """Result of tool execution."""

    success: bool
    output: str | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class AgentExecutionContext:
    """Typed context for agent execution."""

    session_id: str | None = None
    tools: list[ToolDefinition] | None = None
    config: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Section 3: Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class ToolProtocol(Protocol):
    """Protocol for agent tools.

    Tools are the atomic capabilities an agent can invoke during
    reasoning.  Each tool has a name, description, JSON parameter
    schema (for LLM function calling), and an async execute method.

    Satisfied by:
    - @tool decorated functions (FunctionTool)
    - Classes extending Tool base class
    """

    @property
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description for the LLM."""
        ...

    @property
    def parameters_schema(self) -> dict[str, Any]:
        """JSON Schema describing the tool's parameters.

        Auto-generated from type hints by the @tool decorator,
        or manually defined for class-based tools.

        Format follows OpenAI function calling schema::

            {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "reason": {"type": "string"}
                },
                "required": ["order_id"]
            }
        """
        ...

    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with the given arguments.

        Returns the tool's result.  Errors should be raised as
        exceptions — the executor wraps them in Result.
        """
        ...


@runtime_checkable
class AgentProtocol(Protocol):
    """Protocol for AI agents.

    An agent declares its identity, capabilities (tools), and
    persona (system prompt).  The AgentExecutor uses this
    protocol to drive the reasoning loop.
    """

    @property
    def name(self) -> str:
        """Unique agent identifier."""
        ...

    @property
    def tools(self) -> list[ToolProtocol]:
        """Tools available to this agent."""
        ...

    @property
    def system_prompt(self) -> str:
        """System prompt defining the agent's persona and constraints."""
        ...


@runtime_checkable
class StrategyProtocol(Protocol):
    """Protocol for agent reasoning strategies.

    A strategy implements the reasoning loop that drives an agent's
    behavior.  Built-in strategies: ReActStrategy (reason → act →
    observe) and PlanAndExecuteStrategy (plan → execute steps).
    """

    async def execute(
        self,
        message: str,
        tools: list[ToolProtocol],
        history: list[dict[str, Any]],
        llm: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute the reasoning strategy.

        Args:
            message: The user's input message.
            tools: Tools available to the agent.
            history: Conversation history as list of message dicts.
            llm: LLM client for reasoning.
            **kwargs: Additional strategy-specific parameters
                (system_prompt, temperature, tool_registry, etc.)

        Returns:
            Result[AgentResponse, Exception]
        """
        ...


@runtime_checkable
class AgentExecutorProtocol(Protocol):
    """Protocol for agent execution engines.

    The executor runs an agent with governance checks, memory
    management, and observability integration.
    """

    async def run(
        self,
        agent: AgentProtocol,
        message: str,
        session_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute an agent and return the response.

        Returns Result[AgentResponse, AgentError].
        """
        ...

    async def astream(
        self,
        agent: AgentProtocol,
        message: str,
        session_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
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
        ...


@runtime_checkable
class ToolRegistryProtocol(Protocol):
    """Protocol for tool registries.

    A registry stores tools by name and provides execution with
    error handling.  When module visibility is enabled, tool access
    is checked against the compiled module graph.
    """

    def register(
        self,
        tool: ToolProtocol,
        module_class: type | None = None,
    ) -> None:
        """Register a tool."""
        ...

    def get(self, name: str) -> ToolProtocol | None:
        """Get a tool by name."""
        ...

    def list_tools(self) -> list[ToolProtocol]:
        """List all registered tools."""
        ...

    def list_visible_tools(self) -> list[ToolProtocol]:
        """List tools visible to the current caller module."""
        ...

    def list_visible_tool_names(self) -> list[str]:
        """List names of tools visible to the current caller module."""
        ...

    def set_module_graph(self, graph: CompiledModuleGraphProtocol | None) -> None:
        """Set the compiled module graph for visibility enforcement."""
        ...

    def set_caller_module(self, module_class: type | None) -> None:
        """Set the calling module for visibility checks."""
        ...

    async def execute(
        self,
        name: str,
        **kwargs: Any,
    ) -> Result[Any, ToolError]:
        """Execute a tool by name.

        Returns Result[Any, ToolError].
        """
        ...


@runtime_checkable
class MemoryProtocol(Protocol):
    """Protocol for conversation memory."""

    async def add_message(self, message: Any) -> None:
        """Add a message to memory.

        Args:
            message: Message to add.
        """
        ...

    async def get_messages(self) -> list[Any]:
        """Get all messages from memory.

        Returns:
            List of messages.
        """
        ...

    async def clear(self) -> None:
        """Clear all messages from memory."""
        ...


@runtime_checkable
class AgentStrategyProtocol(Protocol):
    """Protocol for pluggable agent reasoning strategies.

    Implementations encode a particular reasoning loop (ReAct,
    Plan-and-Execute, Chain-of-Thought, Reflexion, etc.).
    """

    @property
    def name(self) -> str:
        """Human-readable strategy identifier."""
        ...

    async def run(
        self,
        objective: str,
        context: Any,
    ) -> Result[Any, ToolError]:
        """Execute the reasoning loop for the given objective.

        Args:
            objective: Top-level task description.
            context: Agent execution context (tools, memory, config).

        Returns:
            Strategy-specific result object.
        """
        ...


@runtime_checkable
class SkillComposerProtocol(Protocol):
    """Protocol for composing multiple skills or tools into a pipeline."""

    async def get_tools(self) -> list[Any]:
        """Return all tools provided by composed skills."""
        ...


class RunnableAgentProtocol(Protocol):
    """Protocol for runnable agents (G-05 parity)."""

    async def plan(self, input: str) -> str:
        """Plan the next steps."""
        ...

    async def execute(self, plan: str) -> str:
        """Execute the plan."""
        ...


class AgentExecutor:
    """Execute an agent (like LangChain's AgentExecutor).

    Analogous to LangChain's AgentExecutor for running agents.
    """

    def __init__(self, agent: RunnableAgentProtocol) -> None:
        self.agent = agent

    def run(self, input: str) -> str:
        """Run the agent synchronously."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self.arun(input))

    async def arun(self, input: str) -> str:
        """Run the agent asynchronously."""
        plan = await self.agent.plan(input)
        return await self.agent.execute(plan)


class AgentWithTools:
    """Agent with tools (like LangChain's agent with tools).

    Analogous to LangChain's tool-calling agents.
    """

    def __init__(self, tools: list[Any] | None = None) -> None:
        self.tools = tools or []

    def add_tool(self, tool: Any) -> None:
        self.tools.append(tool)


class PlanExecuteAgent:
    """Plan-then-execute agent (like LangChain's PlanAndExecuteAgent).

    Analogous to LangChain's PlanAndExecuteAgent.
    """

    def __init__(self) -> None:
        pass

    def run(self, input: str) -> str:
        """Run the plan-execute agent."""
        return f"planned and executed: {input}"

    async def arun(self, input: str) -> str:
        """Run the plan-execute agent asynchronously."""
        return f"planned and executed: {input}"


__all__ = [
    "AgentError",
    "AgentEvent",
    "AgentEventType",
    "AgentExecutionContext",
    "AgentExecutor",
    "AgentExecutorProtocol",
    "AgentProtocol",
    "AgentResponse",
    "AgentStrategyProtocol",
    "AgentWithTools",
    "MemoryProtocol",
    "PlanExecuteAgent",
    "RunnableAgentProtocol",
    "SkillComposerProtocol",
    "StrategyError",
    "StrategyProtocol",
    "ToolDefinition",
    "ToolError",
    "ToolProtocol",
    "ToolRegistryProtocol",
    "ToolResult",
]
