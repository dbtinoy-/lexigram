"""Batch Indexing Operations"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from lexigram.logging import get_logger
from lexigram.search.engine import SearchEngine

logger = get_logger(__name__)


@dataclass
class BatchConfig:
    """Batch indexing configuration"""

    batch_size: int = 1000
    max_concurrent_batches: int = 5
    retry_attempts: int = 3
    retry_delay: float = 1.0
    progress_callback: Callable[[int, int], None] | None = None
    error_callback: Callable[[Exception, dict[str, Any]], None] | None = None


@dataclass
class BatchStats:
    """Batch operation statistics"""

    total_documents: int = 0
    processed_documents: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_batches: int = 0
    completed_batches: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration: float | None = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.successful_operations + self.failed_operations
        return self.successful_operations / total if total > 0 else 0.0

    @property
    def throughput(self) -> float:
        """Calculate throughput (docs/second)"""
        if self.duration and self.duration > 0:
            return self.processed_documents / self.duration
        return 0.0


class BatchIndexer:
    """Handles batch indexing operations"""

    def __init__(self, engine: SearchEngine, config: BatchConfig | None = None):
        self.engine = engine
        self.config = config or BatchConfig()
        self._stats = BatchStats()

    async def index_documents(
        self,
        index: str,
        documents: list[dict[str, Any]],
        document_ids: list[str] | None = None,
    ) -> BatchStats:
        """Index multiple documents in batches"""
        self._reset_stats()
        self._stats.total_documents = len(documents)
        self._stats.start_time = datetime.now(UTC)

        try:
            # Prepare operations
            operations = self._prepare_operations(documents, document_ids)

            # Process in batches
            await self._process_batches(index, operations)

        finally:
            self._stats.end_time = datetime.now(UTC)
            if self._stats.start_time and self._stats.end_time:
                self._stats.duration = (
                    self._stats.end_time - self._stats.start_time
                ).total_seconds()

        return self._stats

    async def update_documents(
        self,
        index: str,
        updates: list[dict[str, Any]],
        document_ids: list[str],
    ) -> BatchStats:
        """Update multiple documents in batches"""
        self._reset_stats()
        self._stats.total_documents = len(updates)
        self._stats.start_time = datetime.now(UTC)

        try:
            # Prepare update operations
            operations = []
            for doc_id, update in zip(document_ids, updates, strict=False):
                operations.append(
                    {"operation": "update", "id": doc_id, "document": update},
                )

            # Process in batches
            await self._process_batches(index, operations)

        finally:
            self._stats.end_time = datetime.now(UTC)
            if self._stats.start_time and self._stats.end_time:
                self._stats.duration = (
                    self._stats.end_time - self._stats.start_time
                ).total_seconds()

        return self._stats

    async def delete_documents(self, index: str, document_ids: list[str]) -> BatchStats:
        """Delete multiple documents in batches"""
        self._reset_stats()
        self._stats.total_documents = len(document_ids)
        self._stats.start_time = datetime.now(UTC)

        try:
            # Prepare delete operations
            operations = []
            for doc_id in document_ids:
                operations.append({"operation": "delete", "id": doc_id})

            # Process in batches
            await self._process_batches(index, operations)

        finally:
            self._stats.end_time = datetime.now(UTC)
            if self._stats.start_time and self._stats.end_time:
                self._stats.duration = (
                    self._stats.end_time - self._stats.start_time
                ).total_seconds()

        return self._stats

    def _prepare_operations(
        self,
        documents: list[dict[str, Any]],
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Prepare bulk operations from documents"""
        operations = []

        for i, document in enumerate(documents):
            doc_id = document_ids[i] if document_ids and i < len(document_ids) else None

            if doc_id is None:
                # Try to get ID from document
                doc_id = document.get("id") or document.get("_id") or str(i)

            operations.append(
                {"operation": "index", "id": doc_id, "document": document},
            )

        return operations

    async def _process_batches(
        self,
        index: str,
        operations: list[dict[str, Any]],
    ) -> None:
        """Process operations in batches with double-buffering pipeline.

        Batch preparation (slicing) and network I/O are overlapped via
        ``asyncio.gather``: all batch tasks are launched concurrently and
        the semaphore caps how many are *actively sending* to the backend
        at once, so the next batch's I/O starts as soon as a slot is free.
        This achieves the double-buffering effect without a sequential loop.
        """
        from lexigram.logging import get_logger

        _logger = get_logger(__name__)

        # Split operations into batches
        batches = [
            operations[i : i + self.config.batch_size]
            for i in range(0, len(operations), self.config.batch_size)
        ]

        self._stats.total_batches = len(batches)

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)

        async def process_batch(batch: list[dict[str, Any]], batch_num: int) -> None:
            async with semaphore:
                await self._process_single_batch(index, batch, batch_num)

        # Process batches concurrently
        tasks = [
            process_batch(i_batch[1], i_batch[0]) for i_batch in enumerate(batches)
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_single_batch(
        self,
        index: str,
        operations: list[dict[str, Any]],
        batch_num: int,
    ) -> None:
        """Process a single batch with retry logic"""
        attempt = 0

        while attempt < self.config.retry_attempts:
            try:
                # Execute bulk operation
                result = await self.engine.bulk_operation(index, operations)  # type: ignore[attr-defined]

                # Update statistics
                self._stats.completed_batches += 1
                self._stats.successful_operations += result.successful
                self._stats.failed_operations += result.failed
                self._stats.processed_documents += len(operations)

                # Call progress callback
                if self.config.progress_callback:
                    self.config.progress_callback(
                        self._stats.processed_documents,
                        self._stats.total_documents,
                    )

                # Handle partial failures
                if result.failed > 0 and self.config.error_callback:
                    for failed_op in result.operations:
                        if not failed_op.success and failed_op.error:
                            self.config.error_callback(
                                Exception(failed_op.error),
                                failed_op,
                            )

                break  # Success, exit retry loop

            except (OSError, ValueError, RuntimeError, ConnectionError) as e:
                logger.debug("Bulk operation attempt %s failed: %s", attempt + 1, e)
                attempt += 1

                if attempt >= self.config.retry_attempts:
                    # All retries exhausted
                    self._stats.failed_operations += len(operations)
                    self._stats.processed_documents += len(operations)

                    if self.config.error_callback:
                        for op in operations:
                            self.config.error_callback(e, op)

                    break

                # Wait before retry
                await asyncio.sleep(self.config.retry_delay * attempt)

    def _reset_stats(self) -> None:
        """Reset batch statistics"""
        self._stats = BatchStats()

    def get_stats(self) -> BatchStats:
        """Get current batch statistics"""
        return self._stats


@asynccontextmanager
async def batch_indexing_context(indexer: BatchIndexer) -> Any:
    """Context manager for batch indexing operations"""
    try:
        yield indexer
    finally:
        # Cleanup if needed
        pass


__all__ = ["BatchConfig", "BatchIndexer", "BatchStats", "batch_indexing_context"]
