"""Unit tests for AITracer trace-payload redaction and size capping."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.ai.observability.tracing.core import AITracer
from lexigram.logging.redaction import DefaultRedactor


@pytest.fixture
def mock_tracer() -> MagicMock:
    """Return a mock underlying tracer."""
    return MagicMock()


class TestAITracerRedaction:
    """Tests for key-based redaction at the span-attribute boundary."""

    @pytest.mark.parametrize(
        ("key", "original", "expected"),
        [
            ("password", "hunter2", "<redacted>"),
            ("token", "tok-abc", "<redacted>"),
            ("api_key", "sk-test-123", "<redacted>"),
            ("Authorization", "Bearer abc", "<redacted>"),
            ("secret", "s3cr3t", "<redacted>"),
            ("prompt", "hello world", "hello world"),
            ("tool.name", "calculator", "calculator"),
            ("query", "what is 2+2", "what is 2+2"),
        ],
    )
    async def test_on_tool_start_with_policy_redacts_secret_shaped_keys(
        self,
        mock_tracer: MagicMock,
        key: str,
        original: str,
        expected: str,
    ) -> None:
        """Test tool arguments with secret-shaped keys are redacted."""
        tracer = AITracer(tracer=mock_tracer, redaction_policy=DefaultRedactor())

        await tracer.on_tool_start(tool_name="search", arguments={key: original})

        attributes = mock_tracer.start_span.call_args[1]["attributes"]
        assert attributes["tool.args"][key] == expected

    async def test_on_tool_start_without_policy_passes_arguments_through(
        self, mock_tracer: MagicMock
    ) -> None:
        """Test tool arguments are byte-identical when no policy is set."""
        arguments = {"password": "hunter2", "query": "search me"}
        tracer = AITracer(tracer=mock_tracer)

        await tracer.on_tool_start(tool_name="search", arguments=arguments)

        attributes = mock_tracer.start_span.call_args[1]["attributes"]
        assert attributes["tool.args"] == arguments

    async def test_on_agent_action_with_policy_redacts_nested_secrets(
        self, mock_tracer: MagicMock
    ) -> None:
        """Test nested secret-shaped keys in agent actions are redacted."""
        span = MagicMock()
        mock_tracer.get_current_span.return_value = span
        tracer = AITracer(tracer=mock_tracer, redaction_policy=DefaultRedactor())
        action = {"tool": "search", "credentials": {"api_key": "sk-123"}}

        await tracer.on_agent_action(action=action)

        assert span.add_event.call_args[0] == (
            "agent.action",
            {"tool": "search", "credentials": {"api_key": "<redacted>"}},
        )

    async def test_on_agent_finish_with_policy_redacts_list_items(
        self, mock_tracer: MagicMock
    ) -> None:
        """Test secret-shaped keys nested in lists are redacted."""
        span = MagicMock()
        mock_tracer.get_current_span.return_value = span
        tracer = AITracer(tracer=mock_tracer, redaction_policy=DefaultRedactor())
        response = {"items": [{"token": "abc"}, {"ok": True}]}

        await tracer.on_agent_finish(response=response)

        assert span.add_event.call_args[0] == (
            "agent.finish",
            {"items": [{"token": "<redacted>"}, {"ok": True}]},
        )

    async def test_on_agent_action_without_policy_passes_action_through(
        self, mock_tracer: MagicMock
    ) -> None:
        """Test agent actions are byte-identical when no policy is set."""
        span = MagicMock()
        mock_tracer.get_current_span.return_value = span
        action = {"tool": "search", "password": "hunter2"}
        tracer = AITracer(tracer=mock_tracer)

        await tracer.on_agent_action(action=action)

        assert span.add_event.call_args[0] == ("agent.action", action)

    async def test_on_retriever_start_with_policy_passes_query_and_redacts_kwargs(
        self, mock_tracer: MagicMock
    ) -> None:
        """Test retriever query passes through while secret kwargs are redacted."""
        tracer = AITracer(tracer=mock_tracer, redaction_policy=DefaultRedactor())

        await tracer.on_retriever_start(query="search me", api_key="sk-123")

        attributes = mock_tracer.start_span.call_args[1]["attributes"]
        assert attributes["retriever.query"] == "search me"
        assert attributes["api_key"] == "<redacted>"


class TestAITracerSizeCap:
    """Tests for the size cap, independent of redaction."""

    async def test_max_attribute_length_truncates_oversized_strings(
        self, mock_tracer: MagicMock
    ) -> None:
        """Test string values over the cap are truncated without a policy."""
        tracer = AITracer(tracer=mock_tracer, max_attribute_length=10)

        await tracer.on_tool_start(tool_name="search", arguments={"query": "a" * 100})

        attributes = mock_tracer.start_span.call_args[1]["attributes"]
        assert attributes["tool.args"]["query"] == "a" * 10

    async def test_max_attribute_length_truncates_nested_strings(
        self, mock_tracer: MagicMock
    ) -> None:
        """Test nested dict/list strings are truncated recursively."""
        span = MagicMock()
        mock_tracer.get_current_span.return_value = span
        tracer = AITracer(tracer=mock_tracer, max_attribute_length=5)
        response = {"items": [{"text": "x" * 50}], "summary": "y" * 50}

        await tracer.on_agent_finish(response=response)

        assert span.add_event.call_args[0] == (
            "agent.finish",
            {"items": [{"text": "x" * 5}], "summary": "y" * 5},
        )

    async def test_no_cap_without_max_attribute_length(
        self, mock_tracer: MagicMock
    ) -> None:
        """Test nothing is truncated by default."""
        tracer = AITracer(tracer=mock_tracer)

        await tracer.on_tool_start(tool_name="search", arguments={"query": "a" * 100})

        attributes = mock_tracer.start_span.call_args[1]["attributes"]
        assert attributes["tool.args"]["query"] == "a" * 100

    async def test_cap_applies_alongside_redaction(
        self, mock_tracer: MagicMock
    ) -> None:
        """Test redaction and truncation compose when both are configured."""
        tracer = AITracer(
            tracer=mock_tracer,
            redaction_policy=DefaultRedactor(),
            max_attribute_length=10,
        )

        await tracer.on_retriever_start(query="b" * 100, token="tok-abc")

        attributes = mock_tracer.start_span.call_args[1]["attributes"]
        assert attributes["retriever.query"] == "b" * 10
        assert attributes["token"] == "<redacted>"
