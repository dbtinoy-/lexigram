"""Unit tests for RAG pipeline evaluation and citation enforcement (P7.1, P7.2).

Tests:
- RAGEvaluator.evaluate() runs all sub-evaluators and computes scores
- RAGPipeline.run() triggers auto-evaluation every N requests
- require_citations=True raises MissingCitationsError when no citations
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.rag.config import PipelineConfig
from lexigram.ai.rag.evaluation.evaluator import RAGEvaluator
from lexigram.ai.rag.evaluation.retrieval import (
    RetrievalPrecisionEvaluator,
    RetrievalRecallEvaluator,
)
from lexigram.ai.rag.evaluation.types import EvaluationResult, MetricType, RAGEvaluationReport
from lexigram.ai.rag.exceptions import MissingCitationsError
from lexigram.ai.rag.pipeline.builder import RAGPipeline
from lexigram.ai.rag.pipeline.types import PipelineContext
from lexigram.ai.rag.synthesis.types import SynthesisResult, SynthesisStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_synthesis_result(citations: list | None = None) -> SynthesisResult:
    return SynthesisResult(
        query="What is Python?",
        response="Python is a high-level programming language.",
        strategy=SynthesisStrategy.DIRECT,
        citations=citations if citations is not None else [],
    )


def _make_context(
    synthesis_result: SynthesisResult | None = None,
    query: str = "What is Python?",
) -> PipelineContext:
    context = PipelineContext(query=query)
    context.synthesis_result = synthesis_result
    return context


def _mock_pipeline(config: PipelineConfig, evaluator=None) -> RAGPipeline:
    """Create a RAGPipeline with a mock executor that returns a preset context."""
    pipeline = RAGPipeline(config=config, stages=[], evaluator=evaluator)
    # Patch executor.execute to return a simple context so no stages need to run
    pipeline.executor.execute = AsyncMock(return_value=PipelineContext(query="test"))
    return pipeline


# ---------------------------------------------------------------------------
# P7.1 — RAGEvaluator tests
# ---------------------------------------------------------------------------


class TestRAGEvaluator:
    @pytest.mark.asyncio
    async def test_evaluate_returns_report_with_all_metrics(self):
        evaluator = RAGEvaluator(
            evaluators=[
                RetrievalPrecisionEvaluator(),
                RetrievalRecallEvaluator(),
            ]
        )

        report = await evaluator.evaluate(
            query="test query",
            retrieved_docs=[{"id": "doc1"}, {"id": "doc2"}],
            generated_answer="some answer",
            relevant_doc_ids={"doc1"},
        )

        assert isinstance(report, RAGEvaluationReport)
        assert report.query == "test query"
        assert len(report.results) == 2
        assert report.overall_score >= 0.0
        assert report.overall_score <= 1.0

    @pytest.mark.asyncio
    async def test_evaluate_no_evaluators_returns_zero_score(self):
        evaluator = RAGEvaluator(evaluators=[])

        report = await evaluator.evaluate(
            query="test",
            retrieved_docs=[],
            generated_answer="answer",
        )

        assert report.overall_score == 0.0
        assert report.results == []

    @pytest.mark.asyncio
    async def test_evaluate_stores_retrieved_docs_in_report(self):
        evaluator = RAGEvaluator(evaluators=[RetrievalPrecisionEvaluator()])

        docs = [{"id": "x1"}, {"id": "x2"}]
        report = await evaluator.evaluate(
            query="q",
            retrieved_docs=docs,
            generated_answer="ans",
            relevant_doc_ids={"x1"},
        )

        assert report.retrieved_docs == docs

    @pytest.mark.asyncio
    async def test_evaluate_precision_with_all_relevant(self):
        evaluator = RAGEvaluator(evaluators=[RetrievalPrecisionEvaluator()])

        report = await evaluator.evaluate(
            query="q",
            retrieved_docs=[{"id": "d1"}, {"id": "d2"}],
            generated_answer="answer",
            relevant_doc_ids={"d1", "d2"},
        )

        precision_result = report.get_metric(MetricType.RETRIEVAL_PRECISION)
        assert precision_result is not None
        assert precision_result.score == 1.0

    @pytest.mark.asyncio
    async def test_evaluate_precision_with_none_relevant(self):
        evaluator = RAGEvaluator(evaluators=[RetrievalPrecisionEvaluator()])

        report = await evaluator.evaluate(
            query="q",
            retrieved_docs=[{"id": "d1"}, {"id": "d2"}],
            generated_answer="answer",
            relevant_doc_ids=set(),
        )

        precision_result = report.get_metric(MetricType.RETRIEVAL_PRECISION)
        assert precision_result is not None
        assert precision_result.score == 0.0

    @pytest.mark.asyncio
    async def test_evaluate_with_custom_evaluator(self):
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate = AsyncMock(
            return_value=EvaluationResult(
                metric_type=MetricType.ANSWER_RELEVANCE,
                score=0.85,
            )
        )

        evaluator = RAGEvaluator(evaluators=[mock_evaluator])
        report = await evaluator.evaluate(
            query="q",
            retrieved_docs=[],
            generated_answer="good answer",
        )

        assert len(report.results) == 1
        assert report.results[0].score == 0.85
        assert report.overall_score == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_evaluate_weighted_overall_score(self):
        mock_eval_a = MagicMock()
        mock_eval_a.evaluate = AsyncMock(
            return_value=EvaluationResult(
                metric_type=MetricType.RETRIEVAL_PRECISION,
                score=1.0,
            )
        )
        mock_eval_b = MagicMock()
        mock_eval_b.evaluate = AsyncMock(
            return_value=EvaluationResult(
                metric_type=MetricType.ANSWER_RELEVANCE,
                score=0.5,
            )
        )

        evaluator = RAGEvaluator(
            evaluators=[mock_eval_a, mock_eval_b],
            weights={
                MetricType.RETRIEVAL_PRECISION: 0.3,
                MetricType.ANSWER_RELEVANCE: 0.7,
            },
        )

        report = await evaluator.evaluate(
            query="q", retrieved_docs=[], generated_answer="ans"
        )

        expected = 1.0 * 0.3 + 0.5 * 0.7
        assert report.overall_score == pytest.approx(expected)


# ---------------------------------------------------------------------------
# P7.1 — Auto-evaluation hook in pipeline
# ---------------------------------------------------------------------------


class TestPipelineAutoEvaluation:
    @pytest.mark.asyncio
    async def test_auto_evaluation_not_triggered_when_disabled(self):
        config = PipelineConfig(name="test", auto_evaluate_every_n=None)
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate = AsyncMock()

        pipeline = _mock_pipeline(config, evaluator=mock_evaluator)
        pipeline.executor.execute = AsyncMock(
            return_value=_make_context(
                synthesis_result=_make_synthesis_result()
            )
        )

        await pipeline.run("query 1")

        mock_evaluator.evaluate.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_evaluation_triggered_every_n_requests(self):
        config = PipelineConfig(name="test", auto_evaluate_every_n=3)
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate = AsyncMock(
            return_value=RAGEvaluationReport(
                query="q",
                retrieved_docs=[],
                generated_answer="a",
                overall_score=0.9,
            )
        )

        pipeline = _mock_pipeline(config, evaluator=mock_evaluator)
        pipeline.executor.execute = AsyncMock(
            return_value=_make_context(
                synthesis_result=_make_synthesis_result()
            )
        )

        # Runs 1 and 2: no evaluation
        await pipeline.run("query 1")
        await pipeline.run("query 2")
        mock_evaluator.evaluate.assert_not_called()

        # Run 3: evaluation triggered
        await pipeline.run("query 3")
        mock_evaluator.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_evaluation_result_stored_in_context_metadata(self):
        config = PipelineConfig(name="test", auto_evaluate_every_n=1)
        eval_report = RAGEvaluationReport(
            query="q",
            retrieved_docs=[],
            generated_answer="ans",
            overall_score=0.75,
        )
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate = AsyncMock(return_value=eval_report)

        pipeline = _mock_pipeline(config, evaluator=mock_evaluator)
        synthesis = _make_synthesis_result()
        base_context = _make_context(synthesis_result=synthesis)
        pipeline.executor.execute = AsyncMock(return_value=base_context)

        ctx = await pipeline.run("query")

        assert "evaluation_report" in ctx.metadata
        assert ctx.metadata["evaluation_report"] is eval_report

    @pytest.mark.asyncio
    async def test_auto_evaluation_failure_does_not_break_pipeline(self):
        config = PipelineConfig(name="test", auto_evaluate_every_n=1)
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate = AsyncMock(side_effect=RuntimeError("eval failed"))

        pipeline = _mock_pipeline(config, evaluator=mock_evaluator)
        pipeline.executor.execute = AsyncMock(
            return_value=_make_context(synthesis_result=_make_synthesis_result())
        )

        # Should not raise — evaluation failure is swallowed with a warning
        ctx = await pipeline.run("query")
        assert ctx is not None


# ---------------------------------------------------------------------------
# P7.2 — Citation enforcement
# ---------------------------------------------------------------------------


class TestCitationEnforcement:
    @pytest.mark.asyncio
    async def test_require_citations_raises_when_no_citations(self):
        config = PipelineConfig(name="test", require_citations=True)

        pipeline = _mock_pipeline(config)
        pipeline.executor.execute = AsyncMock(
            return_value=_make_context(
                synthesis_result=_make_synthesis_result(citations=[])
            )
        )

        with pytest.raises(MissingCitationsError):
            await pipeline.run("query")

    @pytest.mark.asyncio
    async def test_require_citations_passes_when_citations_present(self):
        config = PipelineConfig(name="test", require_citations=True)

        pipeline = _mock_pipeline(config)
        pipeline.executor.execute = AsyncMock(
            return_value=_make_context(
                synthesis_result=_make_synthesis_result(
                    citations=[{"source_id": "doc1", "text_span": "Python is..."}]
                )
            )
        )

        ctx = await pipeline.run("query")

        assert ctx.synthesis_result is not None
        assert ctx.synthesis_result.citations != []

    @pytest.mark.asyncio
    async def test_require_citations_default_false_no_error_without_citations(self):
        config = PipelineConfig(name="test")  # require_citations defaults to False

        pipeline = _mock_pipeline(config)
        pipeline.executor.execute = AsyncMock(
            return_value=_make_context(
                synthesis_result=_make_synthesis_result(citations=[])
            )
        )

        # Should not raise
        ctx = await pipeline.run("query")
        assert ctx is not None

    @pytest.mark.asyncio
    async def test_require_citations_no_synthesis_does_not_raise(self):
        """If there is no synthesis result, citation check is skipped."""
        config = PipelineConfig(name="test", require_citations=True)

        pipeline = _mock_pipeline(config)
        pipeline.executor.execute = AsyncMock(
            return_value=_make_context(synthesis_result=None)
        )

        # No synthesis result → citation check skipped
        ctx = await pipeline.run("query")
        assert ctx is not None
