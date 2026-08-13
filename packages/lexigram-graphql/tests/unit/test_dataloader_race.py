# packages/lexigram-graphql/tests/unit/test_dataloader_race.py

import asyncio

import pytest

from lexigram.graphql.dataloader import DataLoaderProtocol


class TestDataLoaderRaceCondition:
    """Test DataLoaderProtocol race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_loads_single_batch(self):
        """Test concurrent loads result in single batch call."""
        call_count = 0

        async def batch_fn(keys: list[int]) -> list[int]:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate DB query
            return list(map(lambda k: k * 2, keys))

        loader = DataLoaderProtocol(batch_fn)

        # Concurrent loads
        results = await asyncio.gather(
            loader.load(1),
            loader.load(2),
            loader.load(3),
        )

        # Should be single batch call
        assert call_count == 1
        assert results == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_high_concurrency_no_races(self):
        """Test high concurrency doesn't cause race conditions."""
        call_count = 0
        lock = asyncio.Lock()

        async def batch_fn(keys: list[int]) -> list[int]:
            nonlocal call_count
            async with lock:
                call_count += 1
            return keys

        loader = DataLoaderProtocol(batch_fn)

        # 100 concurrent loads
        tasks = list(map(lambda i: loader.load(i), range(100)))
        await asyncio.gather(*tasks)

        # Should be small number of batches (1-3 depending on timing)
        assert call_count < 10  # Not 100!

    @pytest.mark.asyncio
    async def test_batch_fn_validation(self):
        """Test batch_fn return value validation."""

        async def bad_batch_fn(keys: list[int]) -> list[int]:
            # Returns wrong number of values!
            return [1, 2]  # Should return len(keys) values

        loader = DataLoaderProtocol(bad_batch_fn)

        with pytest.raises(ValueError, match="Must return same number"):
            await asyncio.gather(
                loader.load(1),
                loader.load(2),
                loader.load(3),
            )
