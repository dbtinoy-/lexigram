"""
Metrics collection for Lexigram Intelligence operations.

This module provides comprehensive metrics collection for:
- LLM operations (requests, tokens, duration, costs)
- Vector store operations (add, search, delete)
- Cache operations (hits, misses)
- RAG pipeline operations (queries, retrievals, latency)

All metrics use lexigram-monitor's MetricsCollectorProtocol for consistent observability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from lexigram.di.decorators import inject
from lexigram.di.markers import Inject

if TYPE_CHECKING:
    from lexigram.contracts.observability.metrics import (
        MetricsCollectorProtocol as MetricsCollectorProtocol,
    )


@inject
class AIMetrics:
    """Centralized metrics collection for intelligence operations.

    Provides counters, gauges, and histograms for tracking:
    - LLM API calls, tokens, costs, and latency
    - Vector store operations and performance
    - Embedding cache hit rates
    - RAG pipeline end-to-end performance

    Example:
        >>> metrics = AIMetrics()
        >>> # Track LLM request
        >>> metrics.llm_requests_total.increment(
        ...     labels={"provider": "openai", "model": "gpt-4", "status": "success"}
        ... )
        >>> # Track tokens
        >>> metrics.llm_tokens_total.increment(
        ...     amount=1500,
        ...     labels={"provider": "openai", "model": "gpt-4", "type": "completion"}
        ... )
        >>> # Track duration
        >>> metrics.llm_duration_seconds.observe(
        ...     value=0.523,
        ...     labels={"provider": "openai", "model": "gpt-4"}
        ... )
    """

    def __init__(
        self,
        collector: Annotated[MetricsCollectorProtocol, Inject] | None = None,
    ) -> None:
        """Initialize intelligence metrics.

        Args:
            collector: Metrics collector to use (DI-injected).
        """
        if collector is None:
            raise ValueError(
                "No metrics collector provided and lexigram-monitor not available",
            )

        self._collector = collector

        # LLM Metrics
        self.llm_requests_total = self._collector.create_counter(
            name="intelligence_llm_requests_total",
            description="Total number of LLM API requests",
        )

        self.llm_tokens_total = self._collector.create_counter(
            name="intelligence_llm_tokens_total",
            description="Total number of tokens processed (prompt + completion)",
        )

        self.llm_duration_seconds = self._collector.create_histogram(
            name="intelligence_llm_duration_seconds",
            description="Duration of LLM API calls in seconds",
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )

        self.llm_cost_dollars = self._collector.create_counter(
            name="intelligence_llm_cost_dollars",
            description="Total cost of LLM API calls in dollars",
        )

        self.llm_active_requests = self._collector.create_gauge(
            name="intelligence_llm_active_requests",
            description="Number of currently active LLM requests",
        )

        # Vector Store Metrics
        self.vector_operations_total = self._collector.create_counter(
            name="intelligence_vector_operations_total",
            description="Total number of vector store operations",
        )

        self.vector_duration_seconds = self._collector.create_histogram(
            name="intelligence_vector_duration_seconds",
            description="Duration of vector store operations in seconds",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        )

        self.vector_documents_total = self._collector.create_counter(
            name="intelligence_vector_documents_total",
            description="Total number of documents in vector operations",
        )

        self.vector_collection_size = self._collector.create_gauge(
            name="intelligence_vector_collection_size",
            description="Number of documents in each vector collection",
        )

        # Embedding Cache Metrics
        self.embedding_cache_hits = self._collector.create_counter(
            name="intelligence_embedding_cache_hits",
            description="Number of embedding cache hits",
        )

        self.embedding_cache_misses = self._collector.create_counter(
            name="intelligence_embedding_cache_misses",
            description="Number of embedding cache misses",
        )

        self.embedding_cache_size = self._collector.create_gauge(
            name="intelligence_embedding_cache_size",
            description="Number of embeddings cached",
        )

        # RAG Pipeline Metrics
        self.rag_queries_total = self._collector.create_counter(
            name="intelligence_rag_queries_total",
            description="Total number of RAG queries processed",
        )

        self.rag_duration_seconds = self._collector.create_histogram(
            name="intelligence_rag_duration_seconds",
            description="Duration of RAG pipeline stages in seconds",
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
        )

        self.rag_documents_retrieved = self._collector.create_histogram(
            name="intelligence_rag_documents_retrieved",
            description="Number of documents retrieved per RAG query",
            buckets=[1, 3, 5, 10, 20, 50, 100],
        )

        self.rag_active_queries = self._collector.create_gauge(
            name="intelligence_rag_active_queries",
            description="Number of currently active RAG queries",
        )

        # Embedding Metrics
        self.embedding_operations_total = self._collector.create_counter(
            name="intelligence_embedding_operations_total",
            description="Total number of embedding operations",
        )

        self.embedding_duration_seconds = self._collector.create_histogram(
            name="intelligence_embedding_duration_seconds",
            description="Duration of embedding operations in seconds",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
        )

        self.embedding_batch_size = self._collector.create_histogram(
            name="intelligence_embedding_batch_size",
            description="Number of texts embedded in a single batch",
            buckets=[1, 5, 10, 25, 50, 100, 250, 500],
        )

        # Document ingestion metrics
        self.document_ingestion_jobs_submitted = self._collector.create_counter(
            "intelligence_document_ingestion_jobs_submitted_total",
            "Total number of document ingestion jobs submitted",
        )
        self.document_ingestion_jobs_completed = self._collector.create_counter(
            "intelligence_document_ingestion_jobs_completed_total",
            "Total number of document ingestion jobs completed",
        )
        self.document_ingestion_jobs_failed = self._collector.create_counter(
            "intelligence_document_ingestion_jobs_failed_total",
            "Total number of document ingestion jobs failed",
        )
        self.document_ingestion_duration_seconds = self._collector.create_histogram(
            "intelligence_document_ingestion_duration_seconds",
            "Document ingestion duration in seconds",
        )
        self.document_chunks_created_total = self._collector.create_counter(
            "intelligence_document_chunks_created_total",
            "Total number of document chunks created",
        )
        self.document_ingestion_workers_active = self._collector.create_gauge(
            "intelligence_document_ingestion_workers_active",
            "Number of active document ingestion workers",
        )

        # Batch embedding metrics
        self.batch_embedding_jobs_submitted = self._collector.create_counter(
            "intelligence_batch_embedding_jobs_submitted_total",
            "Total number of batch embedding jobs submitted",
        )
        self.batch_embedding_jobs_completed = self._collector.create_counter(
            "intelligence_batch_embedding_jobs_completed_total",
            "Total number of batch embedding jobs completed",
        )
        self.batch_embedding_jobs_failed = self._collector.create_counter(
            "intelligence_batch_embedding_jobs_failed_total",
            "Total number of batch embedding jobs failed",
        )
        self.batch_embedding_duration_seconds = self._collector.create_histogram(
            "intelligence_batch_embedding_duration_seconds",
            "Batch embedding duration in seconds",
        )
        self.batch_embedding_texts_processed = self._collector.create_counter(
            "intelligence_batch_embedding_texts_processed_total",
            "Total number of texts processed for embedding",
        )
        self.batch_embedding_workers_active = self._collector.create_gauge(
            "intelligence_batch_embedding_workers_active",
            "Number of active batch embedding workers",
        )

        # Maintenance metrics
        self.maintenance_workers_active = self._collector.create_gauge(
            "intelligence_maintenance_workers_active",
            "Number of active maintenance workers",
        )
        self.maintenance_tasks_completed = self._collector.create_counter(
            "intelligence_maintenance_tasks_completed_total",
            "Total number of maintenance tasks completed",
        )
        self.maintenance_tasks_failed = self._collector.create_counter(
            "intelligence_maintenance_tasks_failed_total",
            "Total number of maintenance tasks failed",
        )
        self.maintenance_task_duration_seconds = self._collector.create_histogram(
            "intelligence_maintenance_task_duration_seconds",
            "Maintenance task duration in seconds",
        )

        # Dead Letter Queue metrics
        self.dlq_workers_active = self._collector.create_gauge(
            "intelligence_dlq_workers_active",
            "Number of active DLQ workers",
        )
        self.dlq_items_total = self._collector.create_gauge(
            "intelligence_dlq_items_total",
            "Total number of items in DLQ",
        )
        self.dlq_items_added = self._collector.create_counter(
            "intelligence_dlq_items_added_total",
            "Total number of items added to DLQ",
        )
        self.dlq_items_retried = self._collector.create_counter(
            "intelligence_dlq_items_retried_total",
            "Total number of DLQ items retried",
        )
        self.dlq_items_archived = self._collector.create_counter(
            "intelligence_dlq_items_archived_total",
            "Total number of DLQ items archived",
        )
        self.dlq_items_deleted = self._collector.create_counter(
            "intelligence_dlq_items_deleted_total",
            "Total number of DLQ items deleted",
        )
        self.dlq_notifications_sent = self._collector.create_counter(
            "intelligence_dlq_notifications_sent_total",
            "Total number of DLQ notifications sent",
        )

    def get_collector(self) -> MetricsCollectorProtocol:
        """Get the underlying metrics collector.

        Returns:
            The MetricsCollectorProtocol instance for advanced usage.
        """
        return self._collector

    def record_completion(
        self,
        provider: str,
        model: str,
        tokens: int,
        cost: float,
    ) -> None:
        """Record a successful LLM completion.

        Args:
            provider: Provider name.
            model: Model identifier.
            tokens: Total tokens consumed.
            cost: Estimated dollar cost.
        """
        self.llm_requests_total.increment(
            labels={"provider": provider, "model": model, "status": "success"},
        )
        self.llm_tokens_total.increment(
            amount=tokens,
            labels={"provider": provider, "model": model, "type": "completion"},
        )
        self.llm_cost_dollars.increment(
            amount=cost,
            labels={"provider": provider, "model": model},
        )

    def record_error(self, provider: str, error_type: str) -> None:
        """Record an LLM or vector store error.

        Args:
            provider: Provider name.
            error_type: Short error category string.
        """
        self.llm_requests_total.increment(
            labels={
                "provider": provider,
                "model": "unknown",
                "status": "error",
                "error_type": error_type,
            },
        )
