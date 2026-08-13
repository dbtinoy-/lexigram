"""Tests for AI exceptions."""

from lexigram.ai.agents.exceptions import (
    AgentConfigurationError,
    AgentExecutionError,
    ToolExecutionError,
)
from lexigram.ai.llm.exceptions import (
    InvalidRequestError,
    LLMAuthenticationError,
    LLMError,
    LLMRateLimitError,
    ModelNotFoundError,
    TokenLimitError,
)
from lexigram.contracts.ai.agents import AgentError
from lexigram.contracts.ai.session import (
    TaskCancelledError,
    TaskError,
    TaskTimeoutError,
    TaskValidationError,
)
from lexigram.contracts.exceptions import LexigramError
from lexigram.contracts.observability.ai import (
    MetricsCollectionError,
    MonitoringError,
    TracingError,
)


class TestAIError:
    """Tests for LexigramError base class."""

    def test_ai_error_instantiation(self) -> None:
        """Should instantiate with message."""
        error = LexigramError("AI error occurred")
        assert "AI error occurred" in str(error)


class TestLLMError:
    """Tests for LLMError."""

    def test_llm_error(self) -> None:
        """Should instantiate."""
        error = LLMError("LLM error")
        assert "LLM error" in str(error)


class TestRateLimitError:
    """Tests for LLMRateLimitError."""

    def test_rate_limit_error(self) -> None:
        """Should instantiate."""
        error = LLMRateLimitError("Rate limit exceeded")
        assert "Rate limit exceeded" in str(error)


class TestAgentError:
    """Tests for AgentError."""

    def test_agent_error(self) -> None:
        """Should instantiate."""
        error = AgentError("Agent error")
        assert "Agent error" in str(error)


class TestAgentConfigurationError:
    """Tests for AgentConfigurationError."""

    def test_agent_configuration_error(self) -> None:
        """Should instantiate."""
        error = AgentConfigurationError("Invalid config")
        assert "Invalid config" in str(error)


class TestAgentExecutionError:
    """Tests for AgentExecutionError."""

    def test_agent_execution_error(self) -> None:
        """Should instantiate."""
        error = AgentExecutionError("Execution failed")
        assert "Execution failed" in str(error)


class TestToolExecutionError:
    """Tests for ToolExecutionError."""

    def test_tool_execution_error(self) -> None:
        """Should instantiate."""
        error = ToolExecutionError("Tool failed")
        assert "Tool failed" in str(error)


class TestAuthenticationError:
    """Tests for LLMAuthenticationError."""

    def test_authentication_error(self) -> None:
        """Should instantiate."""
        error = LLMAuthenticationError("Auth failed")
        assert "Auth failed" in str(error)


class TestInvalidRequestError:
    """Tests for InvalidRequestError."""

    def test_invalid_request_error(self) -> None:
        """Should instantiate."""
        error = InvalidRequestError("Invalid request")
        assert "Invalid request" in str(error)


class TestTokenLimitError:
    """Tests for TokenLimitError."""

    def test_token_limit_error(self) -> None:
        """Should instantiate."""
        error = TokenLimitError("Token limit exceeded")
        assert "Token limit exceeded" in str(error)


class TestModelNotFoundError:
    """Tests for ModelNotFoundError."""

    def test_model_not_found_error(self) -> None:
        """Should instantiate."""
        error = ModelNotFoundError("gpt-5")
        assert "gpt-5" in str(error)


class TestMonitoringError:
    """Tests for MonitoringError."""

    def test_monitoring_error(self) -> None:
        """Should instantiate."""
        error = MonitoringError("Monitoring failed")
        assert "Monitoring failed" in str(error)


class TestMetricsCollectionError:
    """Tests for MetricsCollectionError."""

    def test_metrics_collection_error(self) -> None:
        """Should instantiate."""
        error = MetricsCollectionError("Metrics collection failed")
        assert "Metrics collection failed" in str(error)


class TestTracingError:
    """Tests for TracingError."""

    def test_tracing_error(self) -> None:
        """Should instantiate."""
        error = TracingError("Tracing failed")
        assert "Tracing failed" in str(error)


class TestTaskError:
    """Tests for TaskError."""

    def test_task_error(self) -> None:
        """Should instantiate."""
        error = TaskError("Task error")
        assert "Task error" in str(error)


class TestTaskCancelledError:
    """Tests for TaskCancelledError."""

    def test_task_cancelled_error(self) -> None:
        """Should instantiate."""
        error = TaskCancelledError("Task cancelled")
        assert "Task cancelled" in str(error)


class TestTaskTimeoutError:
    """Tests for TaskTimeoutError."""

    def test_task_timeout_error(self) -> None:
        """Should instantiate."""
        error = TaskTimeoutError("Task timed out")
        assert "Task timed out" in str(error)


class TestTaskValidationError:
    """Tests for TaskValidationError."""

    def test_task_validation_error(self) -> None:
        """Should instantiate."""
        error = TaskValidationError("Task validation failed")
        assert "Task validation failed" in str(error)
