"""Unit tests for AIMetrics methods - increment and observe operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.ai.observability.metrics.core import AIMetrics


class TestAIMetricsMethods:
    """Tests for AIMetrics increment and observe methods."""

    @pytest.fixture
    def mock_collector(self) -> MagicMock:
        """Create a mock metrics collector with counters and histograms."""
        collector = MagicMock()

        mock_counter = MagicMock()
        mock_histogram = MagicMock()

        collector.create_counter.return_value = mock_counter
        collector.create_histogram.return_value = mock_histogram

        return collector

    @pytest.fixture
    def metrics(self, mock_collector: MagicMock) -> AIMetrics:
        """Create AIMetrics instance with mock collector."""
        return AIMetrics(collector=mock_collector)

    def test_increment_llm_requests(
        self, metrics: AIMetrics, mock_collector: MagicMock
    ) -> None:
        """Test that LLM requests counter increments correctly."""
        labels = {"provider": "openai", "model": "gpt-4", "status": "success"}
        metrics.llm_requests_total.increment(amount=1, labels=labels)

        mock_collector.create_counter.return_value.increment.assert_called_once_with(
            amount=1, labels=labels
        )

    def test_increment_llm_tokens(
        self, metrics: AIMetrics, mock_collector: MagicMock
    ) -> None:
        """Test that LLM tokens counter increments correctly."""
        labels = {"provider": "openai", "model": "gpt-4", "type": "completion"}
        metrics.llm_tokens_total.increment(amount=1500, labels=labels)

        mock_collector.create_counter.return_value.increment.assert_called_with(
            amount=1500, labels=labels
        )

    def test_observe_llm_duration(
        self, metrics: AIMetrics, mock_collector: MagicMock
    ) -> None:
        """Test that LLM duration observation records correctly."""
        labels = {"provider": "openai", "model": "gpt-4"}
        metrics.llm_duration_seconds.observe(value=0.523, labels=labels)

        mock_collector.create_histogram.return_value.observe.assert_called_once_with(
            value=0.523, labels=labels
        )

    def test_increment_vector_operations(
        self, metrics: AIMetrics, mock_collector: MagicMock
    ) -> None:
        """Test that vector operations counter increments correctly."""
        labels = {"operation": "search", "provider": "pgvector", "status": "success"}
        metrics.vector_operations_total.increment(amount=1, labels=labels)

        mock_collector.create_counter.return_value.increment.assert_called_with(
            amount=1, labels=labels
        )

    def test_increment_rag_queries(
        self, metrics: AIMetrics, mock_collector: MagicMock
    ) -> None:
        """Test that RAG query counter increments correctly."""
        labels = {"pipeline": "default", "status": "success"}
        metrics.rag_queries_total.increment(amount=1, labels=labels)

        mock_collector.create_counter.return_value.increment.assert_called_with(
            amount=1, labels=labels
        )

    def test_metrics_are_labeled(
        self, metrics: AIMetrics, mock_collector: MagicMock
    ) -> None:
        """Test that labels are applied to all metrics."""
        labels = {"provider": "openai", "model": "gpt-4"}

        metrics.llm_requests_total.increment(amount=1, labels=labels)
        metrics.llm_tokens_total.increment(amount=100, labels=labels)
        metrics.llm_duration_seconds.observe(value=0.5, labels=labels)
        metrics.rag_queries_total.increment(amount=1, labels=labels)
        metrics.vector_operations_total.increment(amount=1, labels=labels)

        calls = mock_collector.create_counter.return_value.increment.call_args_list
        assert len(calls) >= 4

        for c in calls:
            _, kwargs = c
            assert "labels" in kwargs
            assert kwargs["labels"] is not None
