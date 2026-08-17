"""Agent-specific leaf exceptions for the Lexigram AI agents package.

These exceptions are raised during agent construction, execution, tool
invocation, and strategy execution. Base exception classes (AgentError,
ToolError, StrategyError) are imported from
``lexigram.contracts.agents.exceptions``.

This module is the canonical location for all agent leaf exceptions.
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.agents import (
    AgentError,
    StrategyError,
    ToolError,
)


class AgentConfigurationError(AgentError):
    """Invalid agent configuration.

    Raised when an agent is constructed with invalid parameters
    (no tools, no system prompt, invalid strategy, etc.).
    """

    _code: str = "LEX_ERR_AGT_004"

    def __init__(
        self,
        message: str = "Agent configuration error",
        *,
        agent_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if agent_name:
            details["agent"] = agent_name
        super().__init__(message=message, details=details, **kwargs)


class AgentExecutionError(AgentError):
    """Agent execution failed.

    Raised when the agent's reasoning loop encounters an
    unrecoverable error (LLM failure, strategy crash, etc.).
    """

    _code: str = "LEX_ERR_AGT_005"

    def __init__(
        self,
        message: str = "Agent execution failed",
        *,
        agent_name: str | None = None,
        step_number: int | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if agent_name:
            details["agent"] = agent_name
        if step_number is not None:
            details["step"] = step_number
        super().__init__(message=message, details=details, **kwargs)


class ToolNotFoundError(ToolError):
    """Tool not found in registry.

    Raised when the agent tries to call a tool that is not
    registered in the tool registry.
    """

    _code: str = "LEX_ERR_AGT_006"

    def __init__(
        self,
        message: str = "Tool not found",
        *,
        tool_name: str | None = None,
        available_tools: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        if tool_name:
            message = f"{message}: {tool_name}"
        details = kwargs.pop("details", {})
        if tool_name:
            details["tool"] = tool_name
        if available_tools:
            details["available"] = available_tools
        super().__init__(message=message, details=details, **kwargs)


class ToolExecutionError(ToolError):
    """Tool execution failed.

    Raised when a tool raises an exception during execution.
    """

    _code: str = "LEX_ERR_AGT_007"

    def __init__(
        self,
        message: str = "Tool execution failed",
        *,
        tool_name: str | None = None,
        arguments: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if tool_name:
            message = f"{message}: {tool_name}"
        details = kwargs.pop("details", {})
        if tool_name:
            details["tool"] = tool_name
        if arguments:
            details["arguments"] = arguments
        super().__init__(message=message, details=details, **kwargs)


class ToolAccessDeniedError(ToolError):
    """Agent does not have access to this tool.

    Raised when module visibility controls prevent an agent
    from accessing a specific tool.
    """

    _code: str = "LEX_ERR_AGT_008"

    def __init__(
        self,
        message: str = "Tool access denied",
        *,
        tool_name: str | None = None,
        agent_module: str | None = None,
        tool_module: str | None = None,
        **kwargs: Any,
    ) -> None:
        if tool_name:
            message = f"{message}: {tool_name}"
        details = kwargs.pop("details", {})
        if tool_name:
            details["tool"] = tool_name
        if agent_module:
            details["agent_module"] = agent_module
        if tool_module:
            details["tool_module"] = tool_module
        super().__init__(message=message, details=details, **kwargs)


class MaxIterationsExceededError(StrategyError):
    """Agent exceeded maximum reasoning iterations.

    Raised when the agent reaches max_iterations without
    producing a final response.
    """

    _code: str = "LEX_ERR_AGT_009"

    def __init__(
        self,
        message: str = "Maximum iterations exceeded",
        *,
        max_iterations: int | None = None,
        current_iteration: int | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if max_iterations is not None:
            details["max_iterations"] = max_iterations
        if current_iteration is not None:
            details["current_iteration"] = current_iteration
        super().__init__(message=message, details=details, **kwargs)


class BudgetExceededError(AgentError):
    """Agent exceeded its AI governance budget.

    Raised when token usage or cost exceeds configured limits
    before the agent completes its task.
    """

    _code: str = "LEX_ERR_AGT_010"

    def __init__(
        self,
        message: str = "Budget exceeded",
        *,
        budget_type: str | None = None,
        limit: float | None = None,
        used: float | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if budget_type:
            details["budget_type"] = budget_type
        if limit is not None:
            details["limit"] = limit
        if used is not None:
            details["used"] = used
        super().__init__(message=message, details=details, **kwargs)


class ToolValidationError(ToolError):
    """Tool input validation failed.

    Raised when the arguments provided to a tool fail schema
    validation before execution begins.
    """

    _code: str = "LEX_ERR_AGT_011"

    def __init__(
        self,
        message: str = "Tool input validation failed",
        *,
        tool_name: str | None = None,
        field: str | None = None,
        **kwargs: Any,
    ) -> None:
        if tool_name:
            message = f"{message}: {tool_name}"
        details = kwargs.pop("details", {})
        if tool_name:
            details["tool"] = tool_name
        if field:
            details["field"] = field
        super().__init__(message=message, details=details, **kwargs)


__all__ = [
    "AgentConfigurationError",
    "AgentError",
    "AgentExecutionError",
    "BudgetExceededError",
    "MaxIterationsExceededError",
    "StrategyError",
    "ToolAccessDeniedError",
    "ToolError",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolValidationError",
]
