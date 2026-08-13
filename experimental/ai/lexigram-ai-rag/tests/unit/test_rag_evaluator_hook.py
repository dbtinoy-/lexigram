"""Tests for RAG evaluation hooks in the pipeline."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.ai.rag import RAGEvaluatorProtocol


class MockEvaluator:
    """Mock evaluator implementing RAGEvaluatorProtocol."""

    def __init__(self) -> None:
        self.call_count = 0
        self.last_query: str | None = None

    async def evaluate(
        self,
        query: str,
        retrieved_docs: list[Any],
        generated_answer: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.call_count += 1
        self.last_query = query
        return {"score": 0.9, "query": query}


class TestRAGEvaluatorProtocol:
    """Tests for RAGEvaluatorProtocol conformance and pipeline integration."""

    def test_mock_evaluator_satisfies_protocol(self) -> None:
        """MockEvaluator satisfies RAGEvaluatorProtocol."""
        evaluator = MockEvaluator()
        assert isinstance(evaluator, RAGEvaluatorProtocol)

    @pytest.mark.asyncio
    async def test_evaluator_is_called_after_synthesis(self) -> None:
        """When evaluator is set on RAGPipeline, it is called after synthesis."""
        from lexigram.ai.rag.pipeline.builder import RAGPipeline
        from lexigram.ai.rag.config import PipelineConfig
        from lexigram.ai.rag.pipeline.types import PipelineContext, SynthesisResult

        evaluator = MockEvaluator()
        config = MagicMock(spec=PipelineConfig)
        config.auto_evaluate_every_n = 1
        config.require_citations = False
        config.default_error_strategy = MagicMock()
        config.max_retries = 0
        config.retry_delay = 0.0

        # Build pipeline with mock executor that sets synthesis_result
        pipeline = RAGPipeline(
            config=config,
            stages=[],
            evaluator=evaluator,
        )

        # Simulate an executed context with a synthesis result
        context = MagicMock()
        context.query = "test query"
        context.request_id = "req-001"
        context.synthesis_result = MagicMock()
        context.synthesis_result.response = "some answer"
        context.synthesis_result.citations = []
        context.optimized_chunks = []
        context.retrieved_chunks = []
        context.metadata = {}

        pipeline.executor = MagicMock()
        pipeline.executor.execute = AsyncMock(return_value=context)

        await pipeline.run("test query")

        assert evaluator.call_count == 1
        assert evaluator.last_query == "test query"

    @pytest.mark.asyncio
    async def test_pipeline_works_without_evaluator(self) -> None:
        """Pipeline runs successfully when no evaluator is provided."""
        from lexigram.ai.rag.pipeline.builder import RAGPipeline
        from lexigram.ai.rag.config import PipelineConfig

        config = MagicMock(spec=PipelineConfig)
        config.auto_evaluate_every_n = 1
        config.require_citations = False
        config.default_error_strategy = MagicMock()
        config.max_retries = 0
        config.retry_delay = 0.0

        pipeline = RAGPipeline(config=config, stages=[], evaluator=None)

        context = MagicMock()
        context.query = "test query"
        context.request_id = "req-002"
        context.synthesis_result = None
        context.metadata = {}

        pipeline.executor = MagicMock()
        pipeline.executor.execute = AsyncMock(return_value=context)

        result = await pipeline.run("test query")
        assert result is not None
