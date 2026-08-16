"""Batched vector operation utilities."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from lexigram.contracts.data.vector import (
        DeleteResult,
        UpsertResult,
        VectorCollectionProtocol,
        VectorRecord,
    )

T = TypeVar("T")


class BatchProcessor:
    """Helper for executing large-scale vector operations in parallel chunks."""

    def __init__(self, batch_size: int = 100, max_concurrency: int = 5) -> None:
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency

    async def upsert_batches(
        self, collection: VectorCollectionProtocol, records: list[VectorRecord]
    ) -> list[UpsertResult]:
        """Upsert records in batches."""
        batches = [
            records[i : i + self.batch_size]
            for i in range(0, len(records), self.batch_size)
        ]

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _upsert(batch: list[VectorRecord]) -> UpsertResult:
            async with semaphore:
                return await collection.upsert(batch)

        return await asyncio.gather(*[_upsert(b) for b in batches])

    async def delete_batches(
        self, collection: VectorCollectionProtocol, ids: list[str]
    ) -> list[DeleteResult]:
        """Delete records in batches."""
        batches = [
            ids[i : i + self.batch_size] for i in range(0, len(ids), self.batch_size)
        ]

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _delete(batch: list[str]) -> DeleteResult:
            async with semaphore:
                return await collection.delete(batch)

        return await asyncio.gather(*[_delete(b) for b in batches])
