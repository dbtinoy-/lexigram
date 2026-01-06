"""Additional tests for AIMetrics core."""

import pytest
from unittest.mock import MagicMock

from lexigram.ai.observability.metrics.core import AIMetrics


class DummyCollector:
    """Mock collector that returns mock instruments."""

    def create_counter(self, name, description):
        m = MagicMock()
        m.increment = MagicMock()
        return m

    def create_histogram(self, name, description, buckets=None):
        m = MagicMock()
        m.observe = MagicMock()
        return m

    def create_gauge(self, name, description):
        m = MagicMock()
        m.increment = MagicMock()
        m.decrement = MagicMock()
        return m


class TestAIMetricsCreation:
    """Test AIMetrics instantiation."""

    def test_creation_with_collector(self):
        collector = DummyCollector()
        metrics = AIMetrics(collector=collector)
        assert metrics._collector is collector

    def test_creation_without_collector_raises(self):
        with pytest.raises(ValueError, match="No metrics collector"):
            AIMetrics(collector=None)

    def test_get_collector(self):
        collector = DummyCollector()
        metrics = AIMetrics(collector=collector)
        result = metrics.get_collector()
        assert result is collector


class TestAIMetricsLLM:
    """Test LLM metric instruments."""

    def test_llm_instruments_exist(self):
        collector = DummyCollector()
        metrics = AIMetrics(collector=collector)

        assert metrics.llm_requests_total is not None
        assert metrics.llm_tokens_total is not None
        assert metrics.llm_duration_seconds is not None
        assert metrics.llm_cost_dollars is not None
        assert metrics.llm_active_requests is not None


class TestAIMetricsVector:
    """Test vector metric instruments."""

    def test_vector_instruments_exist(self):
        collector = DummyCollector()
        metrics = AIMetrics(collector=collector)

        assert metrics.vector_operations_total is not None
        assert metrics.vector_duration_seconds is not None
        assert metrics.vector_documents_total is not None
        assert metrics.vector_collection_size is not None


class TestAIMetricsCache:
    """Test cache metric instruments."""

    def test_cache_instruments_exist(self):
        collector = DummyCollector()
        metrics = AIMetrics(collector=collector)

        assert metrics.embedding_cache_hits is not None
        assert metrics.embedding_cache_misses is not None
        assert metrics.embedding_cache_size is not None


class TestAIMetricsRAG:
    """Test RAG metric instruments."""

    def test_rag_instruments_exist(self):
        collector = DummyCollector()
        metrics = AIMetrics(collector=collector)

        assert metrics.rag_queries_total is not None
        assert metrics.rag_duration_seconds is not None
        assert metrics.rag_documents_retrieved is not None
        assert metrics.rag_active_queries is not None


class TestAIMetricsEmbedding:
    """Test embedding metric instruments."""

    def test_embedding_instruments_exist(self):
        collector = DummyCollector()
        metrics = AIMetrics(collector=collector)

        assert metrics.embedding_operations_total is not None
        assert metrics.embedding_duration_seconds is not None
        assert metrics.embedding_batch_size is not None


class TestAIMetricsDocumentIngestion:
    """Test document ingestion instruments."""

    def test_document_ingestion_instruments_exist(self):
        collector = DummyCollector()
        metrics = AIMetrics(collector=collector)

        assert metrics.document_ingestion_jobs_submitted is not None
        assert metrics.document_ingestion_jobs_completed is not None
        assert metrics.document_ingestion_jobs_failed is not None
        assert metrics.document_ingestion_duration_seconds is not None
        assert metrics.document_chunks_created_total is not None
        assert metrics.document_ingestion_workers_active is not None


class TestAIMetricsBatchEmbedding:
    """Test batch embedding instruments."""

    def test_batch_embedding_instruments_exist(self):
        collector = DummyCollector()
        metrics = AIMetrics(collector=collector)

        assert metrics.batch_embedding_jobs_submitted is not None
        assert metrics.batch_embedding_jobs_completed is not None
        assert metrics.batch_embedding_jobs_failed is not None
        assert metrics.batch_embedding_duration_seconds is not None
        assert metrics.batch_embedding_texts_processed is not None
        assert metrics.batch_embedding_workers_active is not None


class TestAIMetricsMaintenance:
    """Test maintenance instruments."""

    def test_maintenance_instruments_exist(self):
        collector = DummyCollector()
        metrics = AIMetrics(collector=collector)

        assert metrics.maintenance_workers_active is not None
        assert metrics.maintenance_tasks_completed is not None
        assert metrics.maintenance_tasks_failed is not None
        assert metrics.maintenance_task_duration_seconds is not None


class TestAIMetricsDLQ:
    """Test DLQ instruments."""

    def test_dlq_instruments_exist(self):
        collector = DummyCollector()
        metrics = AIMetrics(collector=collector)

        assert metrics.dlq_workers_active is not None
        assert metrics.dlq_items_total is not None
        assert metrics.dlq_items_added is not None
        assert metrics.dlq_items_retried is not None
        assert metrics.dlq_items_archived is not None
        assert metrics.dlq_items_deleted is not None
        assert metrics.dlq_notifications_sent is not None