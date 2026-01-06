"""
Document ingestion worker.

Main entry point for document ingestion functionality.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.workers.document_ingestion.parser import (
    DocumentParser,
    UniversalDocumentParser,
)
from lexigram.ai.workers.document_ingestion.processor import DocumentProcessor
from lexigram.ai.workers.document_ingestion.progress import ProgressTracker

if TYPE_CHECKING:
    from pathlib import Path

    from lexigram.ai.workers.document_ingestion.types import (
        ChunkingConfigDict,
        IngestionProgress,
        IngestionResult,
    )
    from lexigram.contracts import VectorStoreProtocol
    from lexigram.contracts.infra.tasks import (
        TaskQueueError,
        TaskQueueProtocol,
        TaskWorkerProtocol,
    )
    from lexigram.result import Result

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)

HAS_TASK_WORKER = True

logger = get_logger(__name__)


class DocumentIngestionWorker:
    """Document ingestion worker."""

    def __init__(
        self,
        vector_store: VectorStoreProtocol,
        queue: Any,
        worker_id: str = "document-ingestion",
        concurrency: int = 3,
        default_chunking_config: ChunkingConfigDict | None = None,
        document_parser: DocumentParser | None = None,
    ):
        """
        Initialize document ingestion worker.

        Args:
            vector_store: Vector store for storing document chunks
            queue: Task queue for job management
            worker_id: Unique worker identifier
            concurrency: Number of concurrent document processing tasks
            default_chunking_config: Default chunking configuration
            document_parser: Document parser to use (defaults to UniversalDocumentParser)
        """
        self.vector_store = vector_store
        self.queue = queue
        self.worker_id = worker_id
        self.concurrency = concurrency
        self.default_chunking_config = default_chunking_config or {}
        self.document_parser = document_parser or UniversalDocumentParser()

        # Initialize components
        self.progress_tracker = ProgressTracker()
        self.processor = DocumentProcessor(
            vector_store=vector_store,
            progress_tracker=self.progress_tracker,
            default_chunking_config=self.default_chunking_config,
            document_parser=self.document_parser,
        )

        # TaskWorker resolver happens at module level (see imports above).
        # Use a forward-ref to the TaskWorkerProtocol type so static checkers can
        # validate calls like `.start()` and `.stop()` when the provider is available.
        self._workers: list[TaskWorkerProtocol] = []
        self._running = False

    async def start(self) -> None:
        """Start the ingestion worker pool."""
        if self._running:
            logger.warning("Worker %s already running", self.worker_id)
            return

        self._running = True

        # Create handler registry
        handlers = {
            "ingest_document": self._handle_ingest_document,
        }

        # Start worker pool (if TaskWorker backend is available)
        if not HAS_TASK_WORKER:
            logger.warning(
                "TaskWorker backend not available; worker pool disabled",
                worker_id=self.worker_id,
            )
            # Mark as not running since no workers will be started
            self._running = False
            return

        # Dynamically resolve concrete worker implementation via DI or factory
        # For now, we assume if HAS_TASK_WORKER is true, we can get the implementation
        # usage: container.resolve(TaskWorkerProtocol) or factory pattern
        # Since the original code instantiated TaskWorker directly, we need a way
        # to get the concrete class without importing it here.

        # Strategy: Use DI container to get the factory if available,
        # otherwise we might still need a runtime import inside the method to instantiate
        # IF we want to avoid top-level import.
        # But wait, we want to REMOVE the dependency on concrete class.

        # Ideally:
        # factory = container.resolve("task_worker_factory")
        # worker = factory(...)

        # Current workaround to satisfy the constraint while keeping functionality:
        # Import inside the method (still a violation but scoped) OR use a factory.

        from lexigram.contracts.exceptions import (
            DependencyError,
            UnresolvableDependencyError,
        )
        from lexigram.di.resolution.context import get_resolver

        try:
            # Try to resolve a factory or class
            resolver = get_resolver(self)
            if resolver is None:
                raise ValueError("No resolver found in context")
            worker_class: type[TaskWorkerProtocol] = await cast(
                "Any", resolver
            ).resolve("TaskWorkerClass")
        except (
            DependencyError,
            UnresolvableDependencyError,
            KeyError,
            RuntimeError,
            ValueError,
        ):
            # TaskWorker could not be resolved from the DI container.
            # Without a concrete worker implementation the pool cannot start.
            logger.warning(
                "TaskWorker not resolvable from DI container; "
                "document-ingestion worker pool will not start.  "
                "Register a TaskWorkerProtocol implementation before booting."
            )
            self._running = False
            return

        for i in range(self.concurrency):
            worker = worker_class(
                worker_id=f"{self.worker_id}-{i}",
                queue=self.queue,
                handler_registry=handlers,
            )
            await worker.start()
            self._workers.append(worker)

        logger.info(
            "Started document ingestion worker pool",
            worker_id=self.worker_id,
            concurrency=self.concurrency,
        )

    async def stop(self) -> None:
        """Stop the ingestion worker pool."""
        if not self._running:
            return

        self._running = False

        # Stop all workers
        await asyncio.gather(
            *[worker.stop() for worker in self._workers],
            return_exceptions=True,
        )

        self._workers.clear()

        logger.info("Stopped document ingestion worker pool", worker_id=self.worker_id)

    async def ingest_document(
        self,
        document_id: str,
        file_path: Path,
        collection_name: str,
        parser: DocumentParser | None = None,
        chunking_config: ChunkingConfigDict | None = None,
        metadata: dict[str, Any] | None = None,
        priority: int = 0,
        batch_size: int = 50,
    ) -> str:
        """
        Submit document for ingestion.

        Args:
            document_id: Unique document identifier
            file_path: Path to document file
            collection_name: Vector store collection name
            parser: Optional document parser (uses worker default if None)
            chunking_config: Optional chunking configuration
            metadata: Optional document metadata
            priority: JobProtocol priority (higher = sooner)
            batch_size: Chunks per batch

        Returns:
            JobProtocol ID for tracking
        """
        # Create the job data and enqueue using the TaskQueueProtocol API (avoid
        # instantiating `JobProtocol` directly so providers that expect (job_type, data)
        # usage continue to work and mypy doesn't require concrete JobProtocol types.)
        job_data = {
            "document_id": document_id,
            "file_path": str(file_path),
            "collection_name": collection_name,
            "parser_name": parser.__class__.__name__ if parser else None,
            "metadata": metadata or {},
            "batch_size": batch_size,
        }

        # Initialize progress tracking placeholder will be set after enqueue
        enqueue_result: Result[str, TaskQueueError] = await cast(
            "TaskQueueProtocol", self.queue
        ).enqueue(
            {
                "name": "ingest_document",
                "args": (),
                "kwargs": job_data,
                "priority": priority,
            }
        )
        if enqueue_result.is_err():
            msg = f"Failed to enqueue ingestion job: {enqueue_result.unwrap_err()}"
            raise RuntimeError(msg)

        job_id = enqueue_result.unwrap()
        await self.progress_tracker.initialize_progress(job_id, document_id)

        logger.info(
            "Submitted document ingestion job",
            job_id=job_id,
            document_id=document_id,
            file_path=str(file_path),
        )

        return job_id

    async def get_progress(self, job_id: str) -> IngestionProgress | None:
        """Get ingestion progress for job."""
        return await self.progress_tracker.get_progress(job_id)

    async def _handle_ingest_document(
        self,
        document_id: str,
        file_path: str,
        collection_name: str,
        parser_name: str | None,
        metadata: dict[str, Any],
        batch_size: int = 50,
    ) -> IngestionResult:
        """
        Handle document ingestion job.

        This is the main worker function that processes documents.
        """
        return await self.processor.process_document(
            document_id=document_id,
            file_path=file_path,
            collection_name=collection_name,
            parser_name=parser_name,
            metadata=metadata,
            batch_size=batch_size,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get worker statistics."""
        progress_stats = self.progress_tracker.get_stats()
        return {
            "worker_id": self.worker_id,
            "running": self._running,
            "concurrency": self.concurrency,
            "active_workers": len(self._workers),
            **progress_stats,
        }

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report the health of this worker.

        Args:
            timeout: Unused; present for protocol conformance.

        Returns:
            HEALTHY when the worker is running, UNHEALTHY otherwise.
        """
        status = HealthStatus.HEALTHY if self._running else HealthStatus.UNHEALTHY
        stats = self.get_stats()
        return HealthCheckResult(
            component=f"worker.document_ingestion.{self.worker_id}",
            status=status,
            details=stats,
        )
