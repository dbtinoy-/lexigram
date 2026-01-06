"""Unit tests for GraphQL DataLoaderProtocol."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from lexigram.graphql.dataloader.loader import (
    DataLoaderProtocol,
    create_loader,
    DataLoaderConfig
)

class TestDataLoader:
    """Test DataLoaderProtocol functionality."""

    @pytest.mark.asyncio
    async def test_load_batching(self):
        """Test that requests are batched."""
        batch_fn = AsyncMock()
        batch_fn.return_value = ["A", "B"]
        
        loader = DataLoaderProtocol(batch_fn)
        
        # Load two keys concurrently
        results = await asyncio.gather(
            loader.load(1),
            loader.load(2)
        )
        
        assert results == ["A", "B"]
        # Should be called once with both keys
        batch_fn.assert_called_once_with([1, 2])

    @pytest.mark.asyncio
    async def test_load_caching(self):
        """Test that results are cached."""
        batch_fn = AsyncMock()
        batch_fn.return_value = ["A"]
        
        loader = DataLoaderProtocol(batch_fn)
        
        # First load
        val1 = await loader.load(1)
        assert val1 == "A"
        
        # Second load should hit cache
        val2 = await loader.load(1)
        assert val2 == "A"
        
        # batch_fn should still only be called once
        batch_fn.assert_called_once_with([1])

    @pytest.mark.asyncio
    async def test_prime_cache(self):
        """Test priming the cache."""
        batch_fn = AsyncMock()
        loader = DataLoaderProtocol(batch_fn)
        
        loader.prime(1, "Preloaded")
        
        val = await loader.load(1)
        assert val == "Preloaded"
        batch_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing the cache."""
        batch_fn = AsyncMock()
        batch_fn.side_effect = [["A"], ["A"]]
        
        loader = DataLoaderProtocol(batch_fn)
        
        await loader.load(1)
        loader.clear(1)
        await loader.load(1)
        
        assert batch_fn.call_count == 2

    @pytest.mark.asyncio
    async def test_create_loader_helper(self):
        """Test create_loader helper."""
        batch_fn = AsyncMock()
        loader = create_loader(batch_fn, batch_size=50)
        
        assert isinstance(loader, DataLoaderProtocol)
        assert loader.config.max_batch_size == 50

    @pytest.mark.asyncio
    async def test_batch_size_limit(self):
        """Test max batch size splitting."""
        batch_fn = AsyncMock()
        # Expect two calls if we load 4 items with limit 2
        batch_fn.side_effect = [["A", "B"], ["C", "D"]]
        
        config = DataLoaderConfig(max_batch_size=2)
        loader = DataLoaderProtocol(batch_fn, config=config)
        
        results = await asyncio.gather(
            loader.load(1),
            loader.load(2),
            loader.load(3),
            loader.load(4)
        )
        
        assert results == ["A", "B", "C", "D"]
        assert batch_fn.call_count == 2
