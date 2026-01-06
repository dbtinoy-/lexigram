"""Tests for AI agents exceptions."""

import pytest

from lexigram.ai.agents.exceptions import (
    AgentConfigurationError,
    AgentExecutionError,
    BudgetExceededError,
    MaxIterationsExceededError,
    ToolAccessDeniedError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
)


class TestAgentConfigurationError:
    """Tests for AgentConfigurationError."""

    def test_agent_configuration_error(self) -> None:
        """Test AgentConfigurationError basic."""
        error = AgentConfigurationError("Invalid config")
        assert "Invalid config" in str(error)

    def test_agent_configuration_error_with_agent_name(self) -> None:
        """Test AgentConfigurationError with agent name."""
        error = AgentConfigurationError(
            "Invalid config",
            agent_name="my_agent",
        )
        assert error.details.get("agent") == "my_agent"


class TestAgentExecutionError:
    """Tests for AgentExecutionError."""

    def test_agent_execution_error(self) -> None:
        """Test AgentExecutionError basic."""
        error = AgentExecutionError("Execution failed")
        assert "Execution failed" in str(error)

    def test_agent_execution_error_with_details(self) -> None:
        """Test AgentExecutionError with agent and step."""
        error = AgentExecutionError(
            "Execution failed",
            agent_name="my_agent",
            step_number=5,
        )
        assert error.details.get("agent") == "my_agent"
        assert error.details.get("step") == 5


class TestToolNotFoundError:
    """Tests for ToolNotFoundError."""

    def test_tool_not_found_error(self) -> None:
        """Test ToolNotFoundError basic."""
        error = ToolNotFoundError(tool_name="unknown_tool")
        assert "unknown_tool" in str(error)

    def test_tool_not_found_error_with_available(self) -> None:
        """Test ToolNotFoundError with available tools."""
        error = ToolNotFoundError(
            tool_name="unknown",
            available_tools=["tool1", "tool2"],
        )
        assert error.details.get("available") == ["tool1", "tool2"]


class TestToolExecutionError:
    """Tests for ToolExecutionError."""

    def test_tool_execution_error(self) -> None:
        """Test ToolExecutionError basic."""
        error = ToolExecutionError(tool_name="my_tool")
        assert "my_tool" in str(error)

    def test_tool_execution_error_with_args(self) -> None:
        """Test ToolExecutionError with arguments."""
        error = ToolExecutionError(
            tool_name="my_tool",
            arguments={"key": "value"},
        )
        assert error.details.get("arguments") == {"key": "value"}


class TestToolAccessDeniedError:
    """Tests for ToolAccessDeniedError."""

    def test_tool_access_denied_error(self) -> None:
        """Test ToolAccessDeniedError basic."""
        error = ToolAccessDeniedError(tool_name="restricted_tool")
        assert "restricted_tool" in str(error)

    def test_tool_access_denied_error_modules(self) -> None:
        """Test ToolAccessDeniedError with modules."""
        error = ToolAccessDeniedError(
            tool_name="secret_tool",
            agent_module="agent1",
            tool_module="tools.internal",
        )
        assert error.details.get("agent_module") == "agent1"
        assert error.details.get("tool_module") == "tools.internal"


class TestMaxIterationsExceededError:
    """Tests for MaxIterationsExceededError."""

    def test_max_iterations_exceeded_error(self) -> None:
        """Test MaxIterationsExceededError basic."""
        error = MaxIterationsExceededError()
        assert "Maximum iterations exceeded" in str(error)

    def test_max_iterations_exceeded_error_details(self) -> None:
        """Test MaxIterationsExceededError with iteration details."""
        error = MaxIterationsExceededError(
            max_iterations=10,
            current_iteration=10,
        )
        assert error.details.get("max_iterations") == 10
        assert error.details.get("current_iteration") == 10


class TestBudgetExceededError:
    """Tests for BudgetExceededError."""

    def test_budget_exceeded_error(self) -> None:
        """Test BudgetExceededError basic."""
        error = BudgetExceededError()
        assert "Budget exceeded" in str(error)

    def test_budget_exceeded_error_details(self) -> None:
        """Test BudgetExceededError with budget details."""
        error = BudgetExceededError(
            budget_type="tokens",
            limit=1000,
            used=1100,
        )
        assert error.details.get("budget_type") == "tokens"
        assert error.details.get("limit") == 1000
        assert error.details.get("used") == 1100


class TestToolValidationError:
    """Tests for ToolValidationError."""

    def test_tool_validation_error(self) -> None:
        """Test ToolValidationError basic."""
        error = ToolValidationError()
        assert "Tool input validation failed" in str(error)

    def test_tool_validation_error_with_tool_name(self) -> None:
        """Test ToolValidationError with tool name."""
        error = ToolValidationError(tool_name="my_tool")
        assert "my_tool" in str(error)

    def test_tool_validation_error_with_field(self) -> None:
        """Test ToolValidationError with field."""
        error = ToolValidationError(tool_name="my_tool", field="query")
        assert error.details.get("tool") == "my_tool"
        assert error.details.get("field") == "query"
