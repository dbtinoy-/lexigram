"""Unit tests for observability constants."""

from __future__ import annotations

import pytest


class TestObservabilityConstants:
    """Test observability constants values."""

    def test_env_prefix(self) -> None:
        """Verify environment variable prefix."""
        from lexigram.ai.observability.constants import ENV_PREFIX

        assert ENV_PREFIX == "LEX_AI_OBSERVABILITY__"

    def test_env_nested_delimiter(self) -> None:
        """Verify nested delimiter."""
        from lexigram.ai.observability.constants import ENV_NESTED_DELIMITER

        assert ENV_NESTED_DELIMITER == "__"

    def test_default_check_interval(self) -> None:
        """Verify default health check interval."""
        from lexigram.ai.observability.constants import DEFAULT_CHECK_INTERVAL_SECONDS

        assert DEFAULT_CHECK_INTERVAL_SECONDS == 30

    def test_default_check_timeout(self) -> None:
        """Verify default health check timeout."""
        from lexigram.ai.observability.constants import DEFAULT_CHECK_TIMEOUT_SECONDS

        assert DEFAULT_CHECK_TIMEOUT_SECONDS == 5.0


class TestMetricPrefixes:
    """Test metric name prefixes."""

    def test_llm_metric_prefix(self) -> None:
        """Verify LLM metric prefix."""
        from lexigram.ai.observability.constants import METRIC_PREFIX_LLM

        assert METRIC_PREFIX_LLM == "lexigram.ai.llm"

    def test_vector_metric_prefix(self) -> None:
        """Verify vector metric prefix."""
        from lexigram.ai.observability.constants import METRIC_PREFIX_VECTOR

        assert METRIC_PREFIX_VECTOR == "lexigram.ai.vector"

    def test_embedding_metric_prefix(self) -> None:
        """Verify embedding metric prefix."""
        from lexigram.ai.observability.constants import METRIC_PREFIX_EMBEDDING

        assert METRIC_PREFIX_EMBEDDING == "lexigram.ai.embedding"


class TestSpanNames:
    """Test tracing span names."""

    def test_span_llm_call(self) -> None:
        """Verify LLM call span name."""
        from lexigram.ai.observability.constants import SPAN_LLM_CALL

        assert SPAN_LLM_CALL == "llm.call"

    def test_span_vector_query(self) -> None:
        """Verify vector query span name."""
        from lexigram.ai.observability.constants import SPAN_VECTOR_QUERY

        assert SPAN_VECTOR_QUERY == "vector.query"

    def test_span_embedding_generate(self) -> None:
        """Verify embedding generate span name."""
        from lexigram.ai.observability.constants import SPAN_EMBEDDING_GENERATE

        assert SPAN_EMBEDDING_GENERATE == "embedding.generate"

    def test_span_rag_pipeline(self) -> None:
        """Verify RAG pipeline span name."""
        from lexigram.ai.observability.constants import SPAN_RAG_PIPELINE

        assert SPAN_RAG_PIPELINE == "rag.pipeline"


class TestObservabilityConstantsExports:
    """Test that constants are properly exported."""

    def test_constants_exported(self) -> None:
        """Verify key constants are in __all__."""
        from lexigram.ai.observability import constants

        assert "ENV_PREFIX" in constants.__all__
        assert "DEFAULT_CHECK_INTERVAL_SECONDS" in constants.__all__
        assert "METRIC_PREFIX_LLM" in constants.__all__
        assert "SPAN_LLM_CALL" in constants.__all__