"""Unit tests for FlashRankRerankerStrategy."""

from __future__ import annotations

import asyncio
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock flashrank module before importing the strategy
mock_flashrank = MagicMock()
mock_flashrank.Ranker = MagicMock()
mock_flashrank.RerankRequest = MagicMock()

mock_flashrank.__spec__ = None  # required for importlib.util.find_spec compatibility
sys.modules["flashrank"] = mock_flashrank


class TestFlashRankRerankerStrategy:
    """Tests for FlashRankRerankerStrategy."""

    @pytest.fixture
    def mock_ranker(self) -> MagicMock:
        """Create a mock Ranker instance."""
        ranker = MagicMock()
        ranker.rerank = MagicMock(
            return_value=[
                {"text": "doc2", "score": 0.95},
                {"text": "doc1", "score": 0.85},
                {"text": "doc3", "score": 0.70},
            ]
        )
        return ranker

    @pytest.fixture
    def strategy(self, mock_ranker: MagicMock) -> Any:
        """Create a FlashRankRerankerStrategy with mocked flashrank."""
        with patch.dict(sys.modules, {"flashrank": mock_flashrank}):
            mock_flashrank.Ranker.return_value = mock_ranker
            from lexigram.ai.rag.reranking.strategies.flashrank import (
                FlashRankRerankerStrategy,
            )

            return FlashRankRerankerStrategy()

    @pytest.mark.asyncio
    async def test_rerank_returns_sorted_by_score(self, strategy: Any) -> None:
        """Test that rerank returns results sorted by score descending."""
        result = await strategy.rerank(
            query="test query",
            documents=["doc1", "doc2", "doc3"],
        )

        assert result.documents == ["doc2", "doc1", "doc3"]
        assert result.scores == [0.95, 0.85, 0.70]
        assert result.original_count == 3
        assert result.reranked_count == 3
        assert result.model_name == "ms-marco-MiniLM-L-12-v2"

    @pytest.mark.asyncio
    async def test_rerank_applies_top_k(self, strategy: Any) -> None:
        """Test that rerank applies top_k filter."""
        result = await strategy.rerank(
            query="test query",
            documents=["doc1", "doc2", "doc3"],
            top_k=2,
        )

        assert len(result.documents) == 2
        assert result.documents == ["doc2", "doc1"]
        assert result.scores == [0.95, 0.85]
        assert result.original_count == 3
        assert result.reranked_count == 2

    @pytest.mark.asyncio
    async def test_rerank_no_top_k_returns_all(self, strategy: Any) -> None:
        """Test that rerank returns all documents when top_k is None."""
        result = await strategy.rerank(
            query="test query",
            documents=["doc1", "doc2", "doc3"],
            top_k=None,
        )

        assert result.reranked_count == 3
        assert len(result.documents) == 3

    @pytest.mark.asyncio
    async def test_rerank_runs_in_executor(
        self, strategy: Any, mock_ranker: MagicMock
    ) -> None:
        """Test that rerank calls the ranker via executor."""
        await strategy.rerank(
            query="test query",
            documents=["doc1", "doc2"],
        )

        mock_ranker.rerank.assert_called_once()

    @pytest.mark.asyncio
    async def test_rerank_empty_documents(self, mock_ranker: MagicMock) -> None:
        """Test rerank with empty documents list."""
        mock_ranker.rerank.return_value = []
        with patch.dict(sys.modules, {"flashrank": mock_flashrank}):
            mock_flashrank.Ranker.return_value = mock_ranker
            from lexigram.ai.rag.reranking.strategies.flashrank import (
                FlashRankRerankerStrategy,
            )

            strategy = FlashRankRerankerStrategy()
            result = await strategy.rerank(
                query="test query",
                documents=[],
            )

            assert result.original_count == 0
            assert result.reranked_count == 0


class TestFlashRankStrategyHandler:
    """Tests for FlashRankStrategyHandler."""

    @pytest.fixture
    def handler(self) -> Any:
        """Create a FlashRankStrategyHandler."""
        with patch.dict(sys.modules, {"flashrank": mock_flashrank}):
            mock_ranker = MagicMock()
            mock_ranker.rerank = MagicMock(
                return_value=[
                    {"text": "doc2", "score": 0.95},
                    {"text": "doc1", "score": 0.85},
                ]
            )
            mock_flashrank.Ranker.return_value = mock_ranker

            from lexigram.ai.rag.reranking.strategies.flashrank import (
                FlashRankStrategyHandler,
            )

            return FlashRankStrategyHandler()

    def test_handler_can_handle_flashrank(self, handler: Any) -> None:
        """Test handler can handle 'flashrank' strategy."""
        assert handler.can_handle("flashrank") is True

    def test_handler_cannot_handle_other(self, handler: Any) -> None:
        """Test handler rejects other strategy names."""
        assert handler.can_handle("llmlingua2") is False
        assert handler.can_handle("cross-encoder") is False
        assert handler.can_handle("bge") is False

    def test_handler_lazy_loads_strategy(self) -> None:
        """Test that handler does not load model on __init__ (lazy loading)."""
        with patch.dict(sys.modules, {"flashrank": mock_flashrank}):
            from lexigram.ai.rag.reranking.strategies.flashrank import (
                FlashRankStrategyHandler,
            )

            # Create handler — should not instantiate Ranker yet
            mock_flashrank.Ranker.reset_mock()
            handler = FlashRankStrategyHandler()
            assert mock_flashrank.Ranker.call_count == 0
            assert handler._strategy is None

    @pytest.mark.asyncio
    async def test_handler_create_and_rerank(self) -> None:
        """Test handler create_and_rerank method."""
        with patch.dict(sys.modules, {"flashrank": mock_flashrank}):
            mock_ranker = MagicMock()
            mock_ranker.rerank = MagicMock(
                return_value=[
                    {"text": "doc2", "score": 0.95},
                    {"text": "doc1", "score": 0.85},
                ]
            )
            mock_flashrank.Ranker.return_value = mock_ranker

            from lexigram.ai.rag.reranking.strategies.flashrank import (
                FlashRankStrategyHandler,
            )

            handler = FlashRankStrategyHandler()
            result = await handler.create_and_rerank(
                strategy="flashrank",
                query="test query",
                documents=["doc1", "doc2"],
                model_name="ms-marco-MiniLM-L-12-v2",
                max_length=512,
            )

            assert result.documents == ["doc2", "doc1"]
            assert result.scores == [0.95, 0.85]

    @pytest.mark.asyncio
    async def test_handler_caches_strategy_by_config(self) -> None:
        """Test that handler reuses cached strategy for same config, creates new for different config."""
        with patch.dict(sys.modules, {"flashrank": mock_flashrank}):
            mock_ranker = MagicMock()
            mock_ranker.rerank = MagicMock(
                return_value=[
                    {"text": "doc2", "score": 0.95},
                    {"text": "doc1", "score": 0.85},
                ]
            )
            mock_flashrank.Ranker.return_value = mock_ranker

            from lexigram.ai.rag.reranking.strategies.flashrank import (
                FlashRankStrategyHandler,
            )

            handler = FlashRankStrategyHandler()
            mock_flashrank.Ranker.reset_mock()

            # First call with default config — should create strategy (Ranker called once)
            await handler.create_and_rerank(
                strategy="flashrank",
                query="query1",
                documents=["doc1"],
            )
            assert mock_flashrank.Ranker.call_count == 1
            first_strategy = handler._strategy

            # Second call with same config — should reuse cached strategy (Ranker not called again)
            await handler.create_and_rerank(
                strategy="flashrank",
                query="query2",
                documents=["doc2"],
            )
            assert mock_flashrank.Ranker.call_count == 1  # Still 1, not 2
            assert handler._strategy is first_strategy

            # Third call with different config — should create new strategy (Ranker called again)
            await handler.create_and_rerank(
                strategy="flashrank",
                query="query3",
                documents=["doc3"],
                model_name="different-model",
            )
            assert mock_flashrank.Ranker.call_count == 2
            assert handler._strategy is not first_strategy


class TestFlashRankAvailability:
    """Tests for flashrank availability check."""

    def test_flashrank_available_false_when_not_installed(self) -> None:
        """Test that _flashrank_available returns False when flashrank is not installed."""
        with patch("importlib.util.find_spec") as mock_find_spec:
            from lexigram.ai.rag.reranking.strategies.flashrank import (
                _flashrank_available,
            )

            # Test when flashrank is not available
            mock_find_spec.return_value = None
            assert _flashrank_available() is False

    def test_flashrank_available_true_when_installed(self) -> None:
        """Test that _flashrank_available returns True when flashrank is installed."""
        with patch("importlib.util.find_spec") as mock_find_spec:
            from lexigram.ai.rag.reranking.strategies.flashrank import (
                _flashrank_available,
            )

            # Test when flashrank is available
            mock_find_spec.return_value = MagicMock()
            assert _flashrank_available() is True
