"""More tests for tracing decorators and AITracer."""

import pytest
from unittest.mock import MagicMock

from lexigram.ai.observability.tracing.core import AITracer
from lexigram.contracts.observability.tracing import SpanProtocol as Span


@pytest.fixture
def mock_tracer():
    tracer = MagicMock()
    return tracer


class TestAITracerMethods:
    """Tests for AITracer methods."""

    def test_trace_llm_call_default_attributes(self, mock_tracer):
        ai_tracer = AITracer(tracer=mock_tracer)

        ctx_manager = MagicMock()
        ctx_manager.__enter__.return_value = MagicMock()
        ctx_manager.__exit__.return_value = False
        mock_tracer.start_span.return_value = ctx_manager

        with ai_tracer.trace_llm_call("openai", "gpt-4"):
            pass

        mock_tracer.start_span.assert_called_once()
        call_kwargs = mock_tracer.start_span.call_args[1]
        assert call_kwargs["attributes"]["llm.provider"] == "openai"
        assert call_kwargs["attributes"]["llm.model"] == "gpt-4"

    def test_trace_llm_call_with_extra_attributes(self, mock_tracer):
        ai_tracer = AITracer(tracer=mock_tracer)

        ctx_manager = MagicMock()
        ctx_manager.__enter__.return_value = MagicMock()
        ctx_manager.__exit__.return_value = False
        mock_tracer.start_span.return_value = ctx_manager

        with ai_tracer.trace_llm_call("openai", "gpt-4", custom_attr="value"):
            pass

        call_kwargs = mock_tracer.start_span.call_args[1]
        assert call_kwargs["attributes"]["custom_attr"] == "value"

    def test_trace_vector_operation_without_collection(self, mock_tracer):
        ai_tracer = AITracer(tracer=mock_tracer)

        ctx_manager = MagicMock()
        ctx_manager.__enter__.return_value = MagicMock()
        ctx_manager.__exit__.return_value = False
        mock_tracer.start_span.return_value = ctx_manager

        with ai_tracer.trace_vector_operation("add", "pgvector"):
            pass

        call_kwargs = mock_tracer.start_span.call_args[1]
        assert call_kwargs["attributes"]["vector.operation"] == "add"
        assert call_kwargs["attributes"]["vector.provider"] == "pgvector"

    def test_trace_vector_operation_with_collection(self, mock_tracer):
        ai_tracer = AITracer(tracer=mock_tracer)

        ctx_manager = MagicMock()
        ctx_manager.__enter__.return_value = MagicMock()
        ctx_manager.__exit__.return_value = False
        mock_tracer.start_span.return_value = ctx_manager

        with ai_tracer.trace_vector_operation("search", "pgvector", collection="docs"):
            pass

        call_kwargs = mock_tracer.start_span.call_args[1]
        assert call_kwargs["attributes"]["vector.collection"] == "docs"

    def test_trace_embedding_operation(self, mock_tracer):
        ai_tracer = AITracer(tracer=mock_tracer)

        ctx_manager = MagicMock()
        ctx_manager.__enter__.return_value = MagicMock()
        ctx_manager.__exit__.return_value = False
        mock_tracer.start_span.return_value = ctx_manager

        with ai_tracer.trace_embedding_operation("text-embedding-ada-002", batch_size=10):
            pass

        call_kwargs = mock_tracer.start_span.call_args[1]
        assert call_kwargs["attributes"]["embedding.model"] == "text-embedding-ada-002"
        assert call_kwargs["attributes"]["embedding.batch_size"] == 10

    def test_trace_embedding_operation_no_batch_size(self, mock_tracer):
        ai_tracer = AITracer(tracer=mock_tracer)

        ctx_manager = MagicMock()
        ctx_manager.__enter__.return_value = MagicMock()
        ctx_manager.__exit__.return_value = False
        mock_tracer.start_span.return_value = ctx_manager

        with ai_tracer.trace_embedding_operation("text-embedding-ada-002"):
            pass

        call_kwargs = mock_tracer.start_span.call_args[1]
        assert "embedding.batch_size" not in call_kwargs["attributes"]

    def test_trace_rag_stage(self, mock_tracer):
        ai_tracer = AITracer(tracer=mock_tracer)

        ctx_manager = MagicMock()
        ctx_manager.__enter__.return_value = MagicMock()
        ctx_manager.__exit__.return_value = False
        mock_tracer.start_span.return_value = ctx_manager

        with ai_tracer.trace_rag_stage("retrieval", "default"):
            pass

        call_kwargs = mock_tracer.start_span.call_args[1]
        assert call_kwargs["attributes"]["rag.stage"] == "retrieval"
        assert call_kwargs["attributes"]["rag.pipeline"] == "default"

    def test_trace_rag_query(self, mock_tracer):
        ai_tracer = AITracer(tracer=mock_tracer)

        ctx_manager = MagicMock()
        ctx_manager.__enter__.return_value = MagicMock()
        ctx_manager.__exit__.return_value = False
        mock_tracer.start_span.return_value = ctx_manager

        with ai_tracer.trace_rag_query("What is Python?"):
            pass

        call_kwargs = mock_tracer.start_span.call_args[1]
        assert call_kwargs["attributes"]["rag.query"] == "What is Python?"
        assert call_kwargs["attributes"]["operation.type"] == "rag.query"

    def test_trace_rag_query_truncates_long_queries(self, mock_tracer):
        ai_tracer = AITracer(tracer=mock_tracer)

        long_query = "a" * 200

        ctx_manager = MagicMock()
        ctx_manager.__enter__.return_value = MagicMock()
        ctx_manager.__exit__.return_value = False
        mock_tracer.start_span.return_value = ctx_manager

        with ai_tracer.trace_rag_query(long_query):
            pass

        call_kwargs = mock_tracer.start_span.call_args[1]
        assert len(call_kwargs["attributes"]["rag.query"]) == 100

    def test_trace_operation_generic(self, mock_tracer):
        ai_tracer = AITracer(tracer=mock_tracer)

        ctx_manager = MagicMock()
        ctx_manager.__enter__.return_value = MagicMock()
        ctx_manager.__exit__.return_value = False
        mock_tracer.start_span.return_value = ctx_manager

        with ai_tracer.trace_operation("custom.operation", custom_key="value"):
            pass

        call_kwargs = mock_tracer.start_span.call_args[1]
        assert call_kwargs["attributes"]["custom_key"] == "value"

    def test_get_current_span_returns_none(self, mock_tracer):
        mock_tracer.get_current_span.return_value = None
        ai_tracer = AITracer(tracer=mock_tracer)

        result = ai_tracer.get_current_span()

        assert result is None

    def test_get_current_span_returns_span(self, mock_tracer):
        mock_span = MagicMock()
        mock_tracer.get_current_span.return_value = mock_span
        ai_tracer = AITracer(tracer=mock_tracer)

        result = ai_tracer.get_current_span()

        assert result is mock_span