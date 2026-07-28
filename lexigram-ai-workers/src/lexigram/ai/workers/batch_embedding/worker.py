"""
Main batch embedding worker implementation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.workers.batch_embedding.cache import EmbeddingCache
from lexigram.ai.workers.batch_embedding.progress import ProgressTracker
from lexigram.ai.workers.batch_embedding.types import (
    BatchEmbeddingProgress,
    BatchEmbeddingResult,
    EmbeddingStatus,
)
from lexigram.concurrency import Parallel
from lexigram.contracts.core import ExecutionStrategy
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.workers.batch_embedding.protocols import EmbeddingProvider
    from lexigram.contracts import VectorStoreProtocol
    from lexigram.contracts.ai.rag import ChunkProtocol
    from lexigram.contracts.infra.tasks import TaskQueueProtocol
    from lexigram.contracts.infra.tasks import TaskWorkerProtocol as TaskWorker

logger = get_logger(__name__)


@dataclass(slots=True)
class _EmbeddingChunk:
    """Internal normalized chunk shape for batch embedding jobs."""

    text: str
    metadata: dict[str, Any] | None = None


class BatchEmbeddingWorker:
    """
    Background worker for batch embedding generation.

    Optimizes embedding generation through:
    - Batch processing (minimize API calls)
    - Cache integration (avoid redundant computations)
    - Progress tracking (resumable on failure)
    - Concurrent processing (parallel batches)

    Example:
        ```python
        from lexigram.ai.workers.batch_embedding import BatchEmbeddingWorker
        from lexigram.contracts import VectorStoreProtocol
        from lexigram.contracts.infra.tasks import TaskQueueProtocol

        # Setup — resolve implementations via the DI container
        vector_store = container.resolve(VectorStoreProtocol)
        embedding_provider = container.resolve(EmbeddingClientProtocol)
        queue = container.resolve(TaskQueueProtocol)

        worker = BatchEmbeddingWorker(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            queue=queue,
            concurrency=3,
        )

        # Start worker
        await worker.start()

        # Submit embedding job
        job_id = await worker.embed_batch(
            chunks=chunks,
            collection_name="my-docs",
            model_name="text-embedding-ada-002",
            batch_size=100,
        )

        # Check progress
        progress = await worker.get_progress(job_id)
        logger.info(f"Progress: {progress.progress_percent:.1f}%")
        logger.info(f"Cache hit rate: {progress.cache_hit_rate:.1f}%")

        # Stop worker
        await worker.stop()
        ```
    """

    def __init__(
        self,
        vector_store: VectorStoreProtocol,
        embedding_provider: EmbeddingProvider,
        queue: TaskQueueProtocol,
        worker_id: str = "batch-embedding",
        concurrency: int = 3,
        default_batch_size: int = 100,
        enable_cache: bool = True,
    ):
        """
        Initialize batch embedding worker.

        Args:
            vector_store: Vector store for storing embeddings
            embedding_provider: Provider for generating embeddings
            queue: Task queue for job management
            worker_id: Unique worker identifier
            concurrency: Number of concurrent batch processing tasks
            default_batch_size: Default texts per batch
            enable_cache: Enable embedding cache
        """
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.queue = queue
        self.worker_id = worker_id
        self.concurrency = concurrency
        self.default_batch_size = default_batch_size
        self.enable_cache = enable_cache

        # Component initialization
        self._progress_tracker = ProgressTracker()
        self._cache = EmbeddingCache() if enable_cache else None

        # Worker setup
        self._workers: list[TaskWorker] = []
        self._running = False

    async def start(self) -> None:
        """Start the embedding worker pool."""
        if self._running:
            logger.warning("Worker %s already running", self.worker_id)
            return

        self._running = True

        # Create handler registry
        handlers = {
            "batch_embed": self._handle_batch_embed,
        }

        # Dynamically resolve concrete worker implementation via DI
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
            worker_class: type[TaskWorker] = await cast("Any", resolver).resolve(
                "TaskWorkerClass"
            )
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
                "batch-embedding worker pool will not start.  "
                "Register a TaskWorkerProtocol implementation before booting."
            )
            self._running = False
            return

        # Create workers
        for i in range(self.concurrency):
            worker = worker_class(
                worker_id=f"{self.worker_id}-{i}",
                queue=self.queue,
                handler_registry=handlers,
            )
            self._workers.append(worker)

        # Start all workers concurrently
        start_tasks = [worker.start() for worker in self._workers]
        await Parallel.execute(*start_tasks, strategy=ExecutionStrategy.ALL_SETTLED)

        logger.info(
            "Started batch embedding worker pool",
            worker_id=self.worker_id,
            concurrency=self.concurrency,
        )

    async def stop(self) -> None:
        """Stop the embedding worker pool."""
        if not self._running:
            return

        self._running = False

        # Stop all workers concurrently
        stop_tasks = [worker.stop() for worker in self._workers]
        await Parallel.execute(*stop_tasks, strategy=ExecutionStrategy.ALL_SETTLED)

        self._workers.clear()

        logger.info("Stopped batch embedding worker pool", worker_id=self.worker_id)

    async def embed_batch(
        self,
        chunks: list[ChunkProtocol],
        collection_name: str,
        model_name: str = "text-embedding-ada-002",
        batch_size: int | None = None,
        use_cache: bool = True,
        priority: int = 0,
    ) -> str:
        """
        Submit batch embedding job.

        Args:
            chunks: List of text chunks to embed
            collection_name: Vector store collection name
            model_name: Embedding model name
            batch_size: Texts per batch (default: worker default)
            use_cache: Use embedding cache
            priority: JobProtocol priority (higher = sooner)

        Returns:
            JobProtocol ID for tracking
        """
        if batch_size is None:
            batch_size = self.default_batch_size

        # Create job data
        job_data = {
            "chunks": [{"text": c.text, "metadata": c.metadata or {}} for c in chunks],
            "collection_name": collection_name,
            "model_name": model_name,
            "batch_size": batch_size,
            "use_cache": use_cache and self.enable_cache,
        }

        # Enqueue job
        enqueue_result = await self.queue.enqueue(
            {
                "name": "batch_embed",
                "args": (),
                "kwargs": job_data,
                "priority": priority,
            }
        )
        if enqueue_result.is_err():
            msg = f"Failed to enqueue embedding job: {enqueue_result.unwrap_err()}"
            raise RuntimeError(msg)

        job_id = enqueue_result.unwrap()

        # Initialize progress tracking
        await self._progress_tracker.initialize_job(
            job_id=job_id,
            total_texts=len(chunks),
        )

        logger.info(
            "Submitted batch embedding job",
            job_id=job_id,
            total_chunks=len(chunks),
            batch_size=batch_size,
            model=model_name,
        )

        return job_id

    async def get_progress(self, job_id: str) -> BatchEmbeddingProgress | None:
        """Get embedding progress for job."""
        return await self._progress_tracker.get_progress(job_id)

    async def _handle_batch_embed(
        self,
        chunks: list[dict[str, Any]],
        collection_name: str,
        model_name: str,
        batch_size: int,
        use_cache: bool,
    ) -> BatchEmbeddingResult:
        """
        Handle batch embedding job.

        This is the main worker function that processes embedding batches.
        """
        start_time = asyncio.get_event_loop().time()
        job_id = None  # Will be extracted from context

        # Reconstruct chunks
        chunk_objs = [
            _EmbeddingChunk(
                text=c["text"],
                metadata=c.get("metadata"),
            )
            for c in chunks
        ]

        try:
            # Find job ID from progress
            active_jobs = self._progress_tracker.get_active_jobs()
            for jid in active_jobs:
                progress = await self._progress_tracker.get_progress(jid)
                if (
                    progress
                    and progress.total_texts == len(chunks)
                    and progress.status == EmbeddingStatus.PENDING
                ):
                    job_id = jid
                    break

            if not job_id:
                job_id = f"batch-{datetime.now(UTC).isoformat()}"

            # Update progress: processing
            await self._progress_tracker.update_progress(
                job_id=job_id,
                status=EmbeddingStatus.PROCESSING,
            )

            # Extract texts
            texts = [chunk.text for chunk in chunk_objs]

            # Process in batches
            all_embeddings: list[list[float]] = []
            texts_processed = 0
            cache_hits = 0
            cache_misses = 0

            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]

                # Get embeddings (with or without cache)
                if use_cache and self._cache:
                    (
                        batch_embeddings,
                        hits,
                        misses,
                    ) = await self._cache.get_embeddings_with_cache(
                        batch_texts,
                        model_name,
                        self.embedding_provider,
                    )
                    cache_hits += hits
                    cache_misses += misses
                else:
                    # Generate embeddings without cache
                    batch_embeddings = await self.embedding_provider.embed_texts(
                        batch_texts,
                    )
                    cache_misses += len(batch_texts)

                all_embeddings.extend(batch_embeddings)
                texts_processed += len(batch_texts)

                # Update progress
                await self._progress_tracker.update_progress(
                    job_id=job_id,
                    texts_processed=texts_processed,
                    cache_hits=cache_hits,
                    cache_misses=cache_misses,
                )

                logger.debug(
                    "Processed embedding batch",
                    job_id=job_id,
                    batch_size=len(batch_texts),
                    total_processed=texts_processed,
                    cache_hit_rate=f"{(cache_hits / (cache_hits + cache_misses) * 100):.1f}%",
                )

            # Update progress: storing
            await self._progress_tracker.update_progress(
                job_id=job_id,
                status=EmbeddingStatus.STORING,
            )

            # Store embeddings in vector store
            await self._store_embeddings(
                chunks=chunk_objs,
                embeddings=all_embeddings,
                collection_name=collection_name,
            )

            # Update progress: completed
            await self._progress_tracker.update_progress(
                job_id=job_id,
                status=EmbeddingStatus.COMPLETED,
            )

            duration = asyncio.get_event_loop().time() - start_time

            logger.info(
                "Batch embedding completed",
                job_id=job_id,
                embeddings_generated=len(all_embeddings),
                cache_hits=cache_hits,
                cache_hit_rate=f"{(cache_hits / (cache_hits + cache_misses) * 100):.1f}%",
                duration=f"{duration:.2f}s",
            )

            return BatchEmbeddingResult.success_result(
                job_id=job_id,
                embeddings_generated=len(all_embeddings),
                cache_hits=cache_hits,
                duration=duration,
                metadata={"collection": collection_name, "model": model_name},
            )

        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            error_msg = str(e)

            if job_id:
                await self._progress_tracker.update_progress(
                    job_id=job_id,
                    error=error_msg,
                )

            logger.exception(
                "Batch embedding failed",
                job_id=job_id,
                error=error_msg,
            )

            return BatchEmbeddingResult.failure_result(
                job_id=job_id or "unknown",
                error=error_msg,
                duration=duration,
            )

    async def _store_embeddings(
        self,
        chunks: list[_EmbeddingChunk],
        embeddings: list[list[float]],
        collection_name: str,
    ) -> None:
        """Store embeddings in vector store."""
        # Extract texts and metadata
        texts = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        # Add to vector store with embeddings
        await self.vector_store.add_texts(
            texts=texts,
            embeddings=embeddings,
            metadatas=[m or {} for m in metadatas],
            collection_name=collection_name,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get worker statistics."""
        progress_stats = self._progress_tracker.get_stats()
        cache_size = self._cache.size() if self._cache else 0

        return {
            "worker_id": self.worker_id,
            "running": self._running,
            "concurrency": self.concurrency,
            "active_workers": len(self._workers),
            "cache_size": cache_size,
            "cache_enabled": self.enable_cache,
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
            component=f"worker.batch_embedding.{self.worker_id}",
            status=status,
            details=stats,
        )

    async def clear_cache(self) -> None:
        """Clear the embedding cache."""
        if self._cache:
            await self._cache.clear()
        logger.info("Cleared embedding cache", worker_id=self.worker_id)
