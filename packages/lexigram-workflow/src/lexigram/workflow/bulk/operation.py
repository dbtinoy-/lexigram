"""BulkOperation engine and convenience wrappers."""

from __future__ import annotations

import asyncio
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    cast,
)

from lexigram import serialization as json

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable

    from lexigram.contracts.infra.cache import CacheBackendProtocol
    from lexigram.contracts.infra.resilience import CircuitBreakerProtocol
    from lexigram.workflow.config import BulkOperationConfig

# Type alias used in __init__ signature comments and internal attrs.
# Signature: (processed_count, total_count, message) -> Awaitable[None]
_ProgressHook = "Callable[[int, int, str], Awaitable[None]]"

from lexigram.logging import get_logger
from lexigram.workflow.bulk.models import (
    BulkBatchResult,
    BulkItemError,
    BulkOperationCancelledError,
    BulkOperationError,
    BulkOperationMetrics,
    BulkOperationState,
    BulkOperationTimeoutError,
    R,
    T,
)

_CHECKPOINT_KEY_PREFIX = "lexigram:workflow:bulk:checkpoint:"
_CHECKPOINT_TTL = 86400  # 24 hours

logger = get_logger(__name__)


class BulkOperation(Generic[T, R]):
    """Manages bulk operations with batching, concurrency control, and error handling."""

    def __init__(
        self,
        config: BulkOperationConfig | None = None,
        processor: Callable[[list[T]], Awaitable[list[R]]] | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
        checkpoint_store: CacheBackendProtocol | None = None,
        *,
        on_progress: Callable[[int, int, str], Awaitable[None]] | None = None,
        on_complete: Callable[[int, int, str], Awaitable[None]] | None = None,
        on_error: Callable[[int, int, str], Awaitable[None]] | None = None,
    ) -> None:
        from lexigram.workflow.config import (
            BulkOperationConfig as _BulkOperationConfig,
        )

        self.config = config or _BulkOperationConfig()
        self.processor = processor
        self._state = BulkOperationState.PENDING
        self._metrics = BulkOperationMetrics()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrency)
        self._circuit_breaker: CircuitBreakerProtocol | None = circuit_breaker
        self._checkpoint_store: CacheBackendProtocol | None = checkpoint_store
        self._cancelled = False
        self._allow_variable_results: bool = False
        self._progress_callbacks: list[
            Callable[[BulkOperationMetrics], Awaitable[None]]
        ] = []
        # Lifecycle hooks: (processed_count, total_count, message) -> Awaitable[None]
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error = on_error

    @property
    def state(self) -> BulkOperationState:
        """Get the current operation state."""
        return self._state

    @property
    def metrics(self) -> BulkOperationMetrics:
        """Get operation metrics."""
        return self._metrics

    def add_progress_callback(
        self,
        callback: Callable[[BulkOperationMetrics], Awaitable[None]],
    ) -> None:
        """Add a progress tracking callback."""
        self._progress_callbacks.append(callback)

    async def _notify_progress(self) -> None:
        """Notify all progress callbacks."""
        if self.config.enable_progress_tracking and self._progress_callbacks:
            tasks = [callback(self._metrics) for callback in self._progress_callbacks]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _fire_hook(
        self,
        hook: Callable[[int, int, str], Awaitable[None]] | None,
        message: str,
    ) -> None:
        """Fire a single lifecycle hook if it is registered.

        Errors raised by the hook are logged and swallowed so that a
        misbehaving callback never aborts the bulk operation itself.

        Args:
            hook: The callback to invoke, or ``None`` (no-op).
            message: Human-readable status message passed to the hook.
        """
        if hook is None:
            return
        try:
            await hook(
                self._metrics.processed_items,
                self._metrics.total_items,
                message,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "bulk.hook_error",
                hook=getattr(hook, "__name__", repr(hook)),
                error=str(exc),
            )

    def _chunk_items(self, items: list[T]) -> list[list[T]]:
        """Chunk items into batches."""
        return [
            items[i : i + self.config.batch_size]
            for i in range(0, len(items), self.config.batch_size)
        ]

    def _validate_batch_result_count(self, batch: list[T], results: list[R]) -> None:
        """Validate that processor returned correct number of results."""
        if hasattr(self, "_allow_variable_results") and self._allow_variable_results:
            return  # Allow variable result counts

        if len(results) != len(batch):
            msg = f"Processor returned {len(results)} results but expected {len(batch)}"
            raise BulkOperationError(msg)

    def _should_retry_batch(self, retry_count: int, max_retries: int) -> bool:
        """Check if batch processing should be retried."""
        return retry_count < max_retries

    def _create_batch_error_info(
        self,
        batch_id: int,
        error: Exception,
        retry_count: int,
        end_time: float,
    ) -> BulkItemError:
        """Create structured error information for a failed batch."""
        return BulkItemError(
            batch_id=batch_id,
            error=str(error),
            error_type=type(error).__name__,
            retry_count=retry_count,
            timestamp=end_time,
        )

    async def _process_batch(
        self,
        batch: list[T],
        batch_id: int,
        retry_count: int = 0,
    ) -> BulkBatchResult[T, R]:
        """Process a single batch with retry logic."""
        start_time = time.monotonic()

        try:
            assert self.processor is not None  # noqa: S101  # created in _start_batch before processing

            if self._circuit_breaker:
                results = await self._circuit_breaker.call(
                    cast("Callable[..., Any]", self.processor),
                    batch,
                )
            else:
                results = await self.processor(batch)

            end_time = time.monotonic()
            self._validate_batch_result_count(batch, results)

            return BulkBatchResult(
                batch_id=batch_id,
                items=batch,
                results=results,
                errors=[],
                start_time=start_time,
                end_time=end_time,
                retry_count=retry_count,
            )

        except Exception as e:  # batch operation error boundary; one batch failure must not stop others
            end_time = time.monotonic()
            logger.exception("Error processing batch %s", batch_id)

            error_info = self._create_batch_error_info(
                batch_id,
                e,
                retry_count,
                end_time,
            )

            if self._should_retry_batch(retry_count, self.config.retry_attempts):
                await asyncio.sleep(
                    self.config.retry_delay * (2**retry_count),
                )
                return await self._process_batch(batch, batch_id, retry_count + 1)

            return BulkBatchResult(
                batch_id=batch_id,
                items=batch,
                results=[],
                errors=[error_info],
                start_time=start_time,
                end_time=end_time,
                retry_count=retry_count,
            )

    async def _load_checkpoint(self, operation_id: str) -> set[int]:
        """Load the set of already-completed batch IDs from the checkpoint store.

        Args:
            operation_id: Unique identifier for this bulk operation run.

        Returns:
            Set of completed batch IDs, or empty set if no checkpoint exists.
        """
        if not self._checkpoint_store:
            return set()
        result = await self._checkpoint_store.get(
            f"{_CHECKPOINT_KEY_PREFIX}{operation_id}"
        )
        if result.is_err():
            return set()
        raw = result.unwrap()
        if raw is None:
            return set()
        try:
            if isinstance(raw, bytes):
                raw = raw.decode()
            return set(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            return set()

    async def _save_checkpoint(
        self, operation_id: str, completed_ids: set[int]
    ) -> None:
        """Persist the set of completed batch IDs.

        Args:
            operation_id: Unique identifier for this bulk operation run.
            completed_ids: Set of batch IDs that have completed successfully.
        """
        if not self._checkpoint_store:
            return
        await self._checkpoint_store.set(
            f"{_CHECKPOINT_KEY_PREFIX}{operation_id}",
            json.dumps(sorted(completed_ids)),
            ttl=_CHECKPOINT_TTL,
        )

    async def clear_checkpoint(self, operation_id: str) -> None:
        """Remove a stored checkpoint, allowing the operation to restart from scratch.

        Args:
            operation_id: Unique identifier for the bulk operation run to clear.
        """
        if self._checkpoint_store:
            await self._checkpoint_store.delete(
                f"{_CHECKPOINT_KEY_PREFIX}{operation_id}"
            )

    async def _process_batch_with_semaphore(
        self,
        batch: list[T],
        batch_id: int,
        operation_id: str | None = None,
        completed_ids: set[int] | None = None,
    ) -> BulkBatchResult[T, R]:
        """Process a batch with concurrency control and optional checkpointing."""
        async with self._semaphore:
            if self._cancelled:
                msg = "Bulk operation was cancelled"
                raise BulkOperationCancelledError(msg)

            result = await self._process_batch(batch, batch_id)
            self._metrics.record_batch_result(result)

            if operation_id and completed_ids is not None and not result.errors:
                completed_ids.add(batch_id)
                await self._save_checkpoint(operation_id, completed_ids)

            # Fire the appropriate lifecycle hook.
            if result.errors:
                error_summary = "; ".join(e.error for e in result.errors)
                await self._fire_hook(
                    self._on_error,
                    f"Batch {batch_id} failed: {error_summary}",
                )
            else:
                await self._fire_hook(
                    self._on_progress,
                    f"Processed batch {batch_id}",
                )

            await self._notify_progress()
            return result

    async def execute(
        self,
        items: list[T] | AsyncIterable[T],
        processor: Callable[[list[T]], Awaitable[list[R]]] | None = None,
        operation_id: str | None = None,
    ) -> AsyncIterator[BulkBatchResult[T, R]]:
        """Execute bulk operation on items.

        Args:
            items: Items to process — either a list or an async iterable.
            processor: Optional processor to override the one set at construction.
            operation_id: Stable identifier used for checkpoint/resume.  If supplied
                and a ``checkpoint_store`` was provided at construction, completed
                batches from a previous interrupted run are automatically skipped.
        """
        if self._state != BulkOperationState.PENDING:
            raise BulkOperationError(f"Cannot execute in state: {self._state.value}")

        resolved_processor = processor or self.processor
        if not resolved_processor:
            raise BulkOperationError("No processor function provided")

        if hasattr(items, "__aiter__"):
            collected_items = []
            async for item in items:
                collected_items.append(item)
        else:
            collected_items = items

        batches = self._chunk_items(collected_items)
        self.processor = resolved_processor
        self._state = BulkOperationState.RUNNING
        self._metrics.record_start(len(collected_items), len(batches))

        completed_ids: set[int] = (
            await self._load_checkpoint(operation_id) if operation_id else set()
        )
        if completed_ids:
            logger.info(
                "tasks.bulk.resuming",
                operation_id=operation_id,
                skipping=len(completed_ids),
                total=len(batches),
            )

        tasks = [
            self._process_batch_with_semaphore(
                batch,
                batch_id,
                operation_id=operation_id,
                completed_ids=completed_ids if operation_id else None,
            )
            for batch_id, batch in enumerate(batches)
            if batch_id not in completed_ids
        ]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.timeout,
            )

            for result in results:
                if isinstance(result, Exception):
                    self._metrics.record_error(result)
                else:
                    yield cast("BulkBatchResult[T, R]", result)

            self._state = BulkOperationState.COMPLETED
            await self._fire_hook(
                self._on_complete,
                f"Operation completed: {self._metrics.processed_items}/{self._metrics.total_items} items processed",
            )

        except TimeoutError as te:
            self._cancelled = True
            self._state = BulkOperationState.FAILED
            await self._fire_hook(
                self._on_error,
                f"Operation timed out after {self.config.timeout}s",
            )
            raise BulkOperationTimeoutError(
                f"Bulk operation timed out after {self.config.timeout}s",
            ) from te
        except BaseException as exc:
            self._state = BulkOperationState.FAILED
            await self._fire_hook(
                self._on_error,
                f"Operation failed: {exc}",
            )
            raise
        finally:
            self._metrics.record_end()
            await self._notify_progress()

    async def cancel(self) -> None:
        """Cancel the bulk operation."""
        self._cancelled = True
        self._state = BulkOperationState.CANCELLED

    async def shutdown(self) -> None:
        """Shut down the bulk operation, cancelling any in-progress execution.

        Safe to call even when the operation is not running.  Ensures the
        operation reaches a terminal state so resources can be reclaimed.
        """
        if self._state not in (
            BulkOperationState.COMPLETED,
            BulkOperationState.FAILED,
            BulkOperationState.CANCELLED,
        ):
            await self.cancel()

    async def __aenter__(self) -> BulkOperation[T, R]:
        """Enter the async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit the async context manager, shutting down any active operation."""
        await self.shutdown()


async def bulk_map(
    func: Callable[[T], R],
    items: list[T] | AsyncIterable[T],
    config: BulkOperationConfig | None = None,
) -> list[R]:
    """Apply a function to each item and return results."""

    async def processor(batch: list[T]) -> list[R]:
        return [func(item) for item in batch]

    operation = BulkOperation(config, processor)
    results = []
    async for batch_result in operation.execute(items):
        results.extend(batch_result.results)
    return results


async def bulk_filter(
    items: list[T] | AsyncIterable[T],
    predicate: Callable[[T], Awaitable[bool]],
    config: BulkOperationConfig | None = None,
) -> AsyncIterator[BulkBatchResult[T, T]]:
    """Filter items using a predicate function in batches."""

    async def processor(batch: list[T]) -> list[T]:
        tasks = [predicate(item) for item in batch]
        results = await asyncio.gather(*tasks)
        return [item for item, keep in zip(batch, results, strict=False) if keep]

    operation = BulkOperation(config, processor)
    operation._allow_variable_results = True
    async for result in operation.execute(items):
        yield result


async def bulk_reduce(
    items: list[T] | AsyncIterable[T],
    reducer: Callable[[R, T], Awaitable[R]],
    initial: R,
    config: BulkOperationConfig | None = None,
) -> R:
    """Reduce items using a reducer function sequentially."""
    result = initial
    if hasattr(items, "__aiter__"):
        async for item in items:
            result = await reducer(result, item)
    else:
        for item in items:
            result = await reducer(result, item)
    return result


__all__ = [
    "BulkOperation",
    "bulk_filter",
    "bulk_map",
    "bulk_reduce",
]
