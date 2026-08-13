"""Tests for semantic cache components.

Tests cover:
- SemanticCacheStore three-tier lookup and storage logic
- FaissVectorIndex vector operations (mocked faiss)
- CostAwareCacheDecision cache hit decision logic
- Query normalization and hashing
"""

from __future__ import annotations

import hashlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.cache.semantic.cost_decision import CostAwareCacheDecision
from lexigram.cache.semantic.store import SemanticCacheStore
from lexigram.cache.semantic.vector_index import FaissVectorIndex


class TestSemanticCacheStore:
    """Test suite for SemanticCacheStore."""

    @pytest.fixture
    def mock_cache_backend(self) -> MagicMock:
        """Create a mock CacheBackendProtocol."""
        cache = MagicMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.delete = AsyncMock(return_value=False)
        cache.exists = AsyncMock(return_value=False)
        return cache

    @pytest.fixture
    def mock_embedding_client(self) -> MagicMock:
        """Create a mock EmbeddingClientProtocol."""
        client = MagicMock()
        client.embed = AsyncMock(
            return_value=[[0.1, 0.2, 0.3, 0.4]]  # List of embedding vectors
        )
        return client

    @pytest.fixture
    def mock_vector_index(self) -> MagicMock:
        """Create a mock VectorIndexProtocol."""
        index = MagicMock()
        index.search = AsyncMock(return_value=[])
        index.add = AsyncMock()
        index.remove = AsyncMock(return_value=False)
        index.size = 0
        return index

    @pytest.fixture
    def semantic_cache(
        self,
        mock_cache_backend: MagicMock,
        mock_embedding_client: MagicMock,
        mock_vector_index: MagicMock,
    ) -> SemanticCacheStore:
        """Create a SemanticCacheStore with mocked dependencies."""
        return SemanticCacheStore(
            cache_backend=mock_cache_backend,
            embedding_client=mock_embedding_client,
            vector_index=mock_vector_index,
            similarity_threshold=0.95,
            cache_ttl=None,
        )

    @pytest.mark.asyncio
    async def test_lookup_tier1_exact_match(
        self,
        semantic_cache: SemanticCacheStore,
        mock_cache_backend: MagicMock,
    ) -> None:
        """Tier 1: SHA256 hit returns cached response, no embedding call."""
        query = "What is AI?"
        response = "AI is artificial intelligence"
        mock_cache_backend.get.return_value = response

        result = await semantic_cache.lookup(query)

        assert result == response
        # Verify hash was computed correctly
        expected_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()
        mock_cache_backend.get.assert_called_once_with(expected_hash)

    @pytest.mark.asyncio
    async def test_lookup_tier2_vector_match(
        self,
        semantic_cache: SemanticCacheStore,
        mock_cache_backend: MagicMock,
        mock_embedding_client: MagicMock,
        mock_vector_index: MagicMock,
    ) -> None:
        """Tier 2: SHA256 miss, vector similarity >= threshold returns cached."""
        query = "What is AI?"
        response = "AI is artificial intelligence"
        similar_hash = hashlib.sha256(b"what is artificial intelligence").hexdigest()

        # Tier 1 misses
        mock_cache_backend.get.side_effect = [None, response]

        # Tier 2 finds similar entry with high similarity
        mock_vector_index.search.return_value = [(similar_hash, 0.98)]

        result = await semantic_cache.lookup(query)

        assert result == response
        mock_embedding_client.embed.assert_called_once_with([query])
        mock_vector_index.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_tier3_cache_miss(
        self,
        semantic_cache: SemanticCacheStore,
        mock_cache_backend: MagicMock,
        mock_embedding_client: MagicMock,
        mock_vector_index: MagicMock,
    ) -> None:
        """Tier 3: Both tiers miss returns None."""
        query = "What is AI?"

        # Tier 1 and 2 miss
        mock_cache_backend.get.return_value = None
        mock_vector_index.search.return_value = []

        result = await semantic_cache.lookup(query)

        assert result is None
        mock_embedding_client.embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_tier2_below_threshold(
        self,
        semantic_cache: SemanticCacheStore,
        mock_cache_backend: MagicMock,
        mock_embedding_client: MagicMock,
        mock_vector_index: MagicMock,
    ) -> None:
        """Tier 2: Similarity < threshold falls through to miss."""
        query = "What is AI?"
        similar_hash = hashlib.sha256(b"what is something else").hexdigest()

        # Tier 1 misses
        mock_cache_backend.get.return_value = None

        # Tier 2 finds similar entry with LOW similarity
        mock_vector_index.search.return_value = [(similar_hash, 0.85)]

        result = await semantic_cache.lookup(query)

        assert result is None

    @pytest.mark.asyncio
    async def test_store_writes_both_tiers(
        self,
        semantic_cache: SemanticCacheStore,
        mock_cache_backend: MagicMock,
        mock_embedding_client: MagicMock,
        mock_vector_index: MagicMock,
    ) -> None:
        """Store writes to both cache backend (Tier 1) and vector index (Tier 2)."""
        query = "What is AI?"
        response = "AI is artificial intelligence"
        model = "gpt-4"

        await semantic_cache.store(query, response, model)

        # Verify Tier 1: hash key in cache
        expected_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()
        mock_cache_backend.set.assert_called_once_with(
            expected_hash, response, ttl=None
        )

        # Verify Tier 2: embedding and vector index add
        mock_embedding_client.embed.assert_called_once_with([query])
        mock_vector_index.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_removes_from_both_tiers(
        self,
        semantic_cache: SemanticCacheStore,
        mock_cache_backend: MagicMock,
        mock_vector_index: MagicMock,
    ) -> None:
        """Invalidate removes from both cache backend and vector index."""
        query = "What is AI?"
        expected_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()

        mock_cache_backend.delete.return_value = True
        mock_vector_index.remove.return_value = True

        result = await semantic_cache.invalidate(query)

        assert result is True
        mock_cache_backend.delete.assert_called_once_with(expected_hash)
        mock_vector_index.remove.assert_called_once_with(expected_hash)

    @pytest.mark.asyncio
    async def test_invalidate_not_found(
        self,
        semantic_cache: SemanticCacheStore,
        mock_cache_backend: MagicMock,
        mock_vector_index: MagicMock,
    ) -> None:
        """Invalidate returns False if not found in either tier."""
        query = "What is AI?"

        mock_cache_backend.delete.return_value = False
        mock_vector_index.remove.return_value = False

        result = await semantic_cache.invalidate(query)

        assert result is False

    def test_normalize_query_strips_and_lowercases(
        self,
    ) -> None:
        """Query normalization lowercases and strips whitespace."""
        normalized = SemanticCacheStore._normalize_query("  Hello World  ")
        assert normalized == "hello world"

    def test_semantic_cache_init_invalid_threshold(self) -> None:
        """SemanticCacheStore raises ValueError for invalid similarity threshold."""
        with pytest.raises(ValueError, match="similarity_threshold"):
            SemanticCacheStore(
                cache_backend=MagicMock(),
                embedding_client=MagicMock(),
                vector_index=MagicMock(),
                similarity_threshold=1.5,  # Invalid: > 1
            )

    @pytest.mark.asyncio
    async def test_store_with_ttl(
        self,
        semantic_cache: SemanticCacheStore,
        mock_cache_backend: MagicMock,
    ) -> None:
        """Store respects cache_ttl parameter."""
        semantic_cache._cache_ttl = 300  # 5 minutes

        query = "What is AI?"
        response = "AI is artificial intelligence"

        await semantic_cache.store(query, response, "gpt-4")

        # Verify TTL was passed to cache backend
        call_args = mock_cache_backend.set.call_args
        assert call_args.kwargs.get("ttl") == 300


class TestCostAwareCacheDecision:
    """Test suite for CostAwareCacheDecision."""

    @pytest.fixture
    def decision(self) -> CostAwareCacheDecision:
        """Create a CostAwareCacheDecision with default accuracy weight."""
        return CostAwareCacheDecision(accuracy_weight=0.7)

    def test_cost_aware_decision_uses_cache_high_cost(
        self,
        decision: CostAwareCacheDecision,
    ) -> None:
        """High API cost + high similarity → use cache."""
        # gpt-4: ~$0.03 per 1k tokens
        # expected_tokens: 5000 → ~$0.15
        # similarity: 0.95 → mismatch_penalty = 0.05 * 0.7 = 0.035
        # cost_incentive = min(0.15 * 0.3, 1.0) = 0.045
        # 0.035 < 0.045 → True (use cache)
        result = decision.should_use_cache(
            similarity=0.95,
            api_cost_per_1k_tokens=0.03,
            expected_tokens=5000,
        )
        assert result is True

    def test_cost_aware_decision_skips_cache_low_cost(
        self,
        decision: CostAwareCacheDecision,
    ) -> None:
        """Low API cost + low similarity → skip cache."""
        # gpt-4: ~$0.03 per 1k tokens
        # expected_tokens: 100 → ~$0.003
        # similarity: 0.85 → mismatch_penalty = 0.15 * 0.7 = 0.105
        # cost_incentive = min(0.003 * 0.3, 1.0) = 0.0009
        # 0.105 > 0.0009 → False (skip cache)
        result = decision.should_use_cache(
            similarity=0.85,
            api_cost_per_1k_tokens=0.03,
            expected_tokens=100,
        )
        assert result is False

    def test_cost_aware_decision_zero_cost_never_uses_cache(
        self,
        decision: CostAwareCacheDecision,
    ) -> None:
        """Zero API cost → never use cache."""
        result = decision.should_use_cache(
            similarity=0.99,
            api_cost_per_1k_tokens=0.0,
            expected_tokens=1000,
        )
        assert result is False

    def test_cost_aware_decision_zero_tokens_never_uses_cache(
        self,
        decision: CostAwareCacheDecision,
    ) -> None:
        """Zero expected tokens → never use cache."""
        result = decision.should_use_cache(
            similarity=0.99,
            api_cost_per_1k_tokens=0.03,
            expected_tokens=0,
        )
        assert result is False

    def test_cost_aware_decision_perfect_similarity(
        self,
        decision: CostAwareCacheDecision,
    ) -> None:
        """Perfect similarity (1.0) + any cost → use cache."""
        result = decision.should_use_cache(
            similarity=1.0,
            api_cost_per_1k_tokens=0.001,
            expected_tokens=100,
        )
        assert result is True

    def test_cost_aware_decision_init_invalid_accuracy_weight(self) -> None:
        """CostAwareCacheDecision raises ValueError for invalid accuracy_weight."""
        with pytest.raises(ValueError, match="accuracy_weight"):
            CostAwareCacheDecision(accuracy_weight=1.5)

    def test_cost_aware_decision_init_negative_weight(self) -> None:
        """CostAwareCacheDecision raises ValueError for negative accuracy_weight."""
        with pytest.raises(ValueError, match="accuracy_weight"):
            CostAwareCacheDecision(accuracy_weight=-0.1)

    def test_cost_aware_decision_invalid_similarity(
        self,
        decision: CostAwareCacheDecision,
    ) -> None:
        """should_use_cache raises ValueError for similarity > 1."""
        with pytest.raises(ValueError, match="similarity"):
            decision.should_use_cache(
                similarity=1.5,
                api_cost_per_1k_tokens=0.03,
                expected_tokens=1000,
            )

    def test_cost_aware_decision_invalid_cost(
        self,
        decision: CostAwareCacheDecision,
    ) -> None:
        """should_use_cache raises ValueError for negative cost."""
        with pytest.raises(ValueError, match="api_cost_per_1k_tokens"):
            decision.should_use_cache(
                similarity=0.95,
                api_cost_per_1k_tokens=-0.01,
                expected_tokens=1000,
            )

    def test_cost_aware_decision_invalid_tokens(
        self,
        decision: CostAwareCacheDecision,
    ) -> None:
        """should_use_cache raises ValueError for negative tokens."""
        with pytest.raises(ValueError, match="expected_tokens"):
            decision.should_use_cache(
                similarity=0.95,
                api_cost_per_1k_tokens=0.03,
                expected_tokens=-100,
            )


class TestFaissVectorIndex:
    """Test suite for FaissVectorIndex (mocking faiss).

    Note: These tests use mocked faiss operations since faiss is an optional
    dependency. Real faiss tests would run with the semantic extra installed.
    """

    def test_faiss_index_init_valid_dims(self) -> None:
        """FaissVectorIndex initializes with valid dimensions."""
        pytest.importorskip("faiss")
        index = FaissVectorIndex(embedding_dim=384, max_entries=100_000)
        assert index.size == 0

    def test_faiss_index_init_invalid_dim(self) -> None:
        """FaissVectorIndex raises ValueError for invalid embedding_dim."""
        pytest.importorskip("faiss")
        with pytest.raises(ValueError, match="embedding_dim"):
            FaissVectorIndex(embedding_dim=0)

    def test_faiss_index_init_invalid_max_entries(self) -> None:
        """FaissVectorIndex raises ValueError for invalid max_entries."""
        pytest.importorskip("faiss")
        with pytest.raises(ValueError, match="max_entries"):
            FaissVectorIndex(max_entries=0)

    @pytest.mark.asyncio
    async def test_faiss_index_add_and_search(self) -> None:
        """FaissVectorIndex.add and search work correctly."""
        pytest.importorskip("faiss")
        index = FaissVectorIndex(embedding_dim=4)

        # Normalized vectors (unit length)
        embedding1 = [1.0, 0.0, 0.0, 0.0]  # L2 norm = 1
        embedding2 = [0.7071, 0.7071, 0.0, 0.0]  # sqrt(2)/2, sqrt(2)/2 for L2=1

        await index.add("key1", embedding1)
        await index.add("key2", embedding2)

        assert index.size == 2

        # Search with query similar to embedding1
        results = await index.search(embedding1, k=1)
        assert len(results) == 1
        assert results[0][0] == "key1"
        assert 0.95 < results[0][1] <= 1.0  # High similarity to itself

    @pytest.mark.asyncio
    async def test_faiss_index_add_duplicate_key(self) -> None:
        """FaissVectorIndex skips duplicate keys."""
        pytest.importorskip("faiss")
        index = FaissVectorIndex(embedding_dim=4)
        embedding = [1.0, 0.0, 0.0, 0.0]

        await index.add("key1", embedding)
        assert index.size == 1

        # Adding same key should be skipped
        await index.add("key1", embedding)
        assert index.size == 1

    @pytest.mark.asyncio
    async def test_faiss_index_remove(self) -> None:
        """FaissVectorIndex.remove deletes entries."""
        pytest.importorskip("faiss")
        index = FaissVectorIndex(embedding_dim=4)
        embedding = [1.0, 0.0, 0.0, 0.0]

        await index.add("key1", embedding)
        assert index.size == 1

        result = await index.remove("key1")
        assert result is True
        assert index.size == 0

    @pytest.mark.asyncio
    async def test_faiss_index_remove_not_found(self) -> None:
        """FaissVectorIndex.remove returns False for missing keys."""
        pytest.importorskip("faiss")
        index = FaissVectorIndex(embedding_dim=4)

        result = await index.remove("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_faiss_index_search_empty_index(self) -> None:
        """FaissVectorIndex.search returns [] for empty index."""
        pytest.importorskip("faiss")
        index = FaissVectorIndex(embedding_dim=4)
        embedding = [1.0, 0.0, 0.0, 0.0]

        results = await index.search(embedding, k=1)
        assert results == []

    @pytest.mark.asyncio
    async def test_faiss_index_search_k_larger_than_entries(self) -> None:
        """FaissVectorIndex.search adjusts k to available entries."""
        pytest.importorskip("faiss")
        index = FaissVectorIndex(embedding_dim=4)

        # Add 2 entries
        await index.add("key1", [1.0, 0.0, 0.0, 0.0])
        await index.add("key2", [0.7071, 0.7071, 0.0, 0.0])

        # Request k=5 but only 2 available
        results = await index.search([1.0, 0.0, 0.0, 0.0], k=5)
        assert len(results) == 2  # Should return only 2

    @pytest.mark.asyncio
    async def test_faiss_index_search_after_remove(self) -> None:
        """FaissVectorIndex skips removed entries in search results."""
        pytest.importorskip("faiss")
        index = FaissVectorIndex(embedding_dim=4)

        await index.add("key1", [1.0, 0.0, 0.0, 0.0])
        await index.add("key2", [0.7071, 0.7071, 0.0, 0.0])

        # Remove key1
        await index.remove("key1")

        # Search should only return key2
        results = await index.search([1.0, 0.0, 0.0, 0.0], k=2)
        assert len(results) == 1
        assert results[0][0] == "key2"
