"""Consolidation scheduler — runs periodic consolidation against a MemoryStore."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from lexigram.ai.memory.config import ConsolidationConfig
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.ai.memory import (
        ConsolidationResult,
        MemoryConsolidatorProtocol,
        MemoryStoreProtocol,
    )

logger = get_logger(__name__)


class ConsolidationScheduler:
    """Runs MemoryConsolidator on a configurable interval.

    Designed to be started once and cancelled on shutdown. Consolidation
    is only triggered when the interval elapses and entries are available.
    """

    def __init__(
        self,
        store: MemoryStoreProtocol,
        consolidator: MemoryConsolidatorProtocol,
        config: ConsolidationConfig | None = None,
    ) -> None:
        """Initialise the scheduler.

        Args:
            store: Memory store to read entries from.
            consolidator: Consolidator run on each cycle.
            config: Scheduling configuration.
        """
        self._store = store
        self._consolidator = consolidator
        self._config = config or ConsolidationConfig()
        self._task: asyncio.Task | None = None
        self._background_tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        """Start the background consolidation loop."""
        if not self._config.enabled:
            logger.info("consolidation_scheduler_disabled")
            return
        self._task = asyncio.create_task(self._run_loop())
        self._background_tasks.add(self._task)
        self._task.add_done_callback(self._background_tasks.discard)
        logger.info(
            "consolidation_scheduler_started",
            interval_s=self._config.interval_seconds,
        )

    async def stop(self) -> None:
        """Cancel the background consolidation loop."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("consolidation_scheduler_stopped")

    async def run_once(self) -> ConsolidationResult:
        """Execute a single consolidation pass immediately.

        Returns:
            Result of the consolidation pass.
        """
        entries = await self._store.get_recent(self._config.batch_size * 10)
        return await self._consolidator.consolidate(entries)

    async def _run_loop(self) -> None:
        while True:
            await asyncio.sleep(self._config.interval_seconds)
            try:
                result = await self.run_once()
                logger.debug(
                    "consolidation_cycle",
                    processed=result.entries_processed,
                    pruned=result.entries_pruned,
                )
            except asyncio.CancelledError:
                raise
            except MemoryError as exc:
                logger.error("consolidation_memory_error", error=str(exc))
            except RuntimeError as exc:
                logger.error("consolidation_runtime_error", error=str(exc))


__all__ = ["ConsolidationScheduler"]
