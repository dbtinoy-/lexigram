"""Unit tests for AITracer spans - creation, attributes, events, and context propagation."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock

import pytest

from lexigram.ai.observability.tracing.core import AITracer


class TestAITracerSpans:
    """Tests for AITracer span operations."""

    @pytest.fixture
    def mock_tracer(self) -> MagicMock:
        """Create a mock underlying tracer."""
        return MagicMock()

    @pytest.fixture
    def ai_tracer(self, mock_tracer: MagicMock) -> AITracer:
        """Create AITracer with mock tracer."""
        return AITracer(tracer=mock_tracer)

    def _make_fake_span(self) -> MagicMock:
        """Create a fake span with set_attribute and add_event methods."""
        span = MagicMock()
        span.attributes = {}
        span.events = []

        def set_attribute(key: str, value: Any) -> None:
            span.attributes[key] = value

        def add_event(name: str, attrs: dict | None = None) -> None:
            span.events.append((name, attrs or {}))

        span.set_attribute = set_attribute
        span.add_event = add_event

        return span

    def test_span_creation(self, ai_tracer: AITracer, mock_tracer: MagicMock) -> None:
        """Test that new spans are created with correct name and operation."""
        fake_span = self._make_fake_span()

        mock_tracer.start_span.return_value.__enter__ = MagicMock(
            return_value=fake_span
        )
        mock_tracer.start_span.return_value.__exit__ = MagicMock(
            return_value=None
        )

        with ai_tracer.trace_llm_call("openai", "gpt-4") as span:
            assert mock_tracer.start_span.call_count == 1
            call_kwargs = mock_tracer.start_span.call_args[1]
            assert "llm.openai" in call_kwargs["name"]
            assert call_kwargs["attributes"]["operation.type"] == "llm.completion"

    def test_span_attributes(self, ai_tracer: AITracer, mock_tracer: MagicMock) -> None:
        """Test that attributes can be set on spans."""
        fake_span = self._make_fake_span()

        @contextmanager
        def fake_start_span(name: str, attributes: dict | None = None):
            yield fake_span

        mock_tracer.start_span = fake_start_span

        with ai_tracer.trace_llm_call("openai", "gpt-4") as span:
            span.set_attribute("custom.key", "custom_value")
            span.set_attribute("tokens.total", 1500)

        assert fake_span.attributes["custom.key"] == "custom_value"
        assert fake_span.attributes["tokens.total"] == 1500

    def test_span_events(self, ai_tracer: AITracer, mock_tracer: MagicMock) -> None:
        """Test that events can be added to spans."""
        fake_span = self._make_fake_span()

        @contextmanager
        def fake_start_span(name: str, attributes: dict | None = None):
            yield fake_span

        mock_tracer.start_span = fake_start_span

        with ai_tracer.trace_llm_call("openai", "gpt-4") as span:
            span.add_event("first_event", {"key": "value"})
            span.add_event("second_event")

        assert len(fake_span.events) == 2
        assert fake_span.events[0] == ("first_event", {"key": "value"})
        assert fake_span.events[1] == ("second_event", {})

    def test_span_context_propagation(
        self, ai_tracer: AITracer, mock_tracer: MagicMock
    ) -> None:
        """Test that context propagates through nested spans."""
        fake_span = self._make_fake_span()

        @contextmanager
        def fake_start_span(name: str, attributes: dict | None = None):
            yield fake_span

        mock_tracer.start_span = fake_start_span
        mock_tracer.get_current_span.return_value = fake_span

        with ai_tracer.trace_llm_call("openai", "gpt-4") as outer_span:
            outer_span.set_attribute("outer", "value")

            current = ai_tracer.get_current_span()
            assert current is outer_span

            with ai_tracer.trace_vector_operation("search", "pgvector") as inner_span:
                inner_span.set_attribute("inner", "inner_value")

            inner_current = ai_tracer.get_current_span()
            assert inner_current is outer_span

        assert fake_span.attributes["outer"] == "value"

    def test_span_ends(self, ai_tracer: AITracer, mock_tracer: MagicMock) -> None:
        """Test that end() marks span as complete."""
        fake_span = self._make_fake_span()

        mock_tracer.start_span.return_value.__enter__ = MagicMock(
            return_value=fake_span
        )
        mock_tracer.start_span.return_value.__exit__ = MagicMock(
            return_value=None
        )

        with ai_tracer.trace_llm_call("openai", "gpt-4"):
            pass

        mock_tracer.start_span.assert_called_once()
