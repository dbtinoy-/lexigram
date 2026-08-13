"""RAG benchmarking harness for comparing pipeline configurations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import time
from typing import Any

from lexigram.ai.rag.evaluation.evaluator import RAGEvaluator
from lexigram.ai.rag.evaluation.retrieval import (
    RetrievalPrecisionEvaluator,
    RetrievalRecallEvaluator,
)
from lexigram.ai.rag.evaluation.types import MetricType, RAGEvaluationReport
from lexigram.contracts.ai.rag import RAGContext, RAGPipelineProtocol
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


@dataclass
class EvalExample:
    """A single benchmark example with ground truth.

    Attributes:
        query: The query to evaluate.
        relevant_doc_ids: Ground-truth relevant document identifiers.
        reference_answer: Optional reference answer for answer-quality metrics.
        metadata: Arbitrary metadata attached to this example.
    """

    query: str
    relevant_doc_ids: list[str]
    reference_answer: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Result of running a single pipeline on a single example.

    Attributes:
        pipeline_name: Identifier of the pipeline that produced this result.
        query: The query that was evaluated.
        retrieved_doc_ids: Identifiers of documents returned by the pipeline.
        answer: Generated answer.
        latency_ms: End-to-end latency in milliseconds.
        error: Error message if the pipeline failed.
    """

    pipeline_name: str
    query: str
    retrieved_doc_ids: list[str]
    answer: str
    latency_ms: float
    error: str | None = None


@dataclass
class BenchmarkReport:
    """Comparative benchmark report across multiple RAG pipelines.

    Attributes:
        pipeline_names: Names of all benchmarked pipelines.
        total_examples: Number of evaluation examples used.
        per_pipeline: Mapping of pipeline name → metric name → mean score.
        best_pipeline: Name of the pipeline with the highest overall score.
        generated_at: When this report was produced.
        raw_results: Per-pipeline per-example evaluation reports,
            keyed by pipeline name.
    """

    pipeline_names: list[str]
    total_examples: int
    per_pipeline: dict[str, dict[str, float]]
    best_pipeline: str | None = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    raw_results: dict[str, list[RAGEvaluationReport]] = field(default_factory=dict)

    def summary_table(self) -> list[dict[str, Any]]:
        """Return per-pipeline metric scores as a list of row dicts.

        Each row has a ``pipeline`` key plus one key per metric.

        Returns:
            List of dicts suitable for tabular display.
        """
        rows = []
        for name in self.pipeline_names:
            row: dict[str, Any] = {"pipeline": name}
            row.update(self.per_pipeline.get(name, {}))
            rows.append(row)
        return rows


class RAGBenchmark:
    """Compare RAG pipeline configurations on a labelled dataset.

    Runs every pipeline against every example in the dataset, evaluates
    retrieval and (optionally) answer quality, then aggregates scores
    per pipeline.

    Example:
        >>> dataset = [EvalExample(query="...", relevant_doc_ids=["doc1"])]
        >>> report = await RAGBenchmark().run({"pipe_a": pipeline_a}, dataset)
        >>> print(report.best_pipeline)
    """

    def __init__(
        self,
        evaluator: RAGEvaluator | None = None,
        *,
        max_concurrency: int = 5,
    ) -> None:
        """Initialise the benchmark harness.

        Args:
            evaluator: Optional pre-configured :class:`RAGEvaluator`.  When
                ``None`` a default evaluator with retrieval-precision and
                retrieval-recall is used.
            max_concurrency: Maximum number of pipeline-example pairs that are
                evaluated simultaneously.
        """
        self._evaluator = evaluator or RAGEvaluator(
            evaluators=[
                RetrievalPrecisionEvaluator(),
                RetrievalRecallEvaluator(),
            ]
        )
        self._max_concurrency = max_concurrency

    async def run(
        self,
        pipelines: dict[str, RAGPipelineProtocol],
        dataset: list[EvalExample],
        metrics: list[MetricType] | None = None,
    ) -> BenchmarkReport:
        """Run the benchmark and return a comparative report.

        For each (pipeline, example) pair the pipeline is executed, latency
        is recorded, retrieval metrics are computed, and (when a
        reference answer is provided) answer-quality metrics are computed too.

        Args:
            pipelines: Mapping of display-name → pipeline instance.
            dataset: List of evaluation examples with ground-truth labels.
            metrics: Subset of :class:`MetricType` to include in the report.
                Defaults to all metrics produced by the evaluator.

        Returns:
            :class:`BenchmarkReport` with per-pipeline mean scores.
        """
        if not pipelines:
            return BenchmarkReport(
                pipeline_names=[],
                total_examples=len(dataset),
                per_pipeline={},
            )

        semaphore = asyncio.Semaphore(self._max_concurrency)
        pipeline_names = list(pipelines.keys())

        # raw_eval_results[pipeline_name] = list of RAGEvaluationReport
        raw_eval_results: dict[str, list[RAGEvaluationReport]] = {
            name: [] for name in pipeline_names
        }

        # Build all (pipeline_name, pipeline, example) tasks
        tasks = [
            (name, pipelines[name], example)
            for name in pipeline_names
            for example in dataset
        ]

        async def _run_one(
            pipeline_name: str,
            pipeline: RAGPipelineProtocol,
            example: EvalExample,
        ) -> tuple[str, RAGEvaluationReport | None]:
            async with semaphore:
                return await self._evaluate_one(pipeline_name, pipeline, example)

        coros = [_run_one(name, pipeline, example) for name, pipeline, example in tasks]
        results = await asyncio.gather(*coros, return_exceptions=False)

        for pipeline_name, eval_report in results:
            if eval_report is not None:
                raw_eval_results[pipeline_name].append(eval_report)

        # Aggregate per pipeline
        per_pipeline = self._aggregate(raw_eval_results, metrics)

        # Determine best pipeline by overall score
        best = self._best_pipeline(per_pipeline)

        return BenchmarkReport(
            pipeline_names=pipeline_names,
            total_examples=len(dataset),
            per_pipeline=per_pipeline,
            best_pipeline=best,
            raw_results=raw_eval_results,
        )

    async def _evaluate_one(
        self,
        pipeline_name: str,
        pipeline: RAGPipelineProtocol,
        example: EvalExample,
    ) -> tuple[str, RAGEvaluationReport | None]:
        """Execute the pipeline and evaluate a single example.

        Args:
            pipeline_name: Display name of the pipeline.
            pipeline: Pipeline instance to execute.
            example: Evaluation example.

        Returns:
            Tuple of (pipeline_name, evaluation_report_or_None).
        """
        t0 = time.monotonic()
        context = RAGContext(query=example.query)

        try:
            pipeline_result = await pipeline.execute(context)
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            logger.warning(
                "benchmark: pipeline error",
                pipeline=pipeline_name,
                query=example.query,
                error=str(exc),
            )
            return pipeline_name, None

        latency_ms = (time.monotonic() - t0) * 1000.0

        if pipeline_result.is_err():
            logger.warning(
                "benchmark: pipeline returned error",
                pipeline=pipeline_name,
                query=example.query,
                error=str(pipeline_result.unwrap_err()),
            )
            return pipeline_name, None

        rag_response = pipeline_result.unwrap()

        # Extract retrieved doc IDs from sources
        retrieved_doc_ids: list[str] = []
        for source in rag_response.sources:
            doc_id = getattr(source, "id", None) or getattr(
                getattr(source, "document", None), "id", None
            )
            if doc_id is not None:
                retrieved_doc_ids.append(str(doc_id))

        eval_report = await self._evaluator.evaluate(
            query=example.query,
            retrieved_docs=retrieved_doc_ids,
            generated_answer=rag_response.answer,
            reference_answer=example.reference_answer,
            relevant_doc_ids=example.relevant_doc_ids,
            metadata={
                "pipeline": pipeline_name,
                "latency_ms": latency_ms,
                **example.metadata,
            },
        )

        # Inject latency as a metric result if not already present
        if eval_report.get_metric(MetricType.LATENCY) is None:
            from lexigram.ai.rag.evaluation.types import EvaluationResult

            eval_report.results.append(
                EvaluationResult(
                    metric_type=MetricType.LATENCY,
                    score=latency_ms,
                    details={"latency_ms": latency_ms},
                )
            )

        return pipeline_name, eval_report

    def _aggregate(
        self,
        raw: dict[str, list[RAGEvaluationReport]],
        metrics: list[MetricType] | None,
    ) -> dict[str, dict[str, float]]:
        """Compute mean score per metric per pipeline.

        Args:
            raw: Per-pipeline list of evaluation reports.
            metrics: Optional metric subset filter.

        Returns:
            Mapping of pipeline_name → metric_name → mean_score.
        """
        per_pipeline: dict[str, dict[str, float]] = {}

        for pipeline_name, reports in raw.items():
            if not reports:
                per_pipeline[pipeline_name] = {}
                continue

            # Accumulate scores per metric
            sums: dict[str, float] = {}
            counts: dict[str, int] = {}

            for report in reports:
                for result in report.results:
                    if metrics and result.metric_type not in metrics:
                        continue
                    key = result.metric_type.value
                    sums[key] = sums.get(key, 0.0) + result.score
                    counts[key] = counts.get(key, 0) + 1

            per_pipeline[pipeline_name] = {
                key: sums[key] / counts[key] for key in sums if counts[key] > 0
            }

        return per_pipeline

    def _best_pipeline(
        self,
        per_pipeline: dict[str, dict[str, float]],
    ) -> str | None:
        """Identify the pipeline with the highest mean overall score.

        Latency and cost metrics are excluded from the ranking since lower
        values are better for those and they are on a different scale.

        Args:
            per_pipeline: Aggregated per-pipeline metric scores.

        Returns:
            Name of the best pipeline, or ``None`` if no data is available.
        """
        _excluded = {MetricType.LATENCY.value, MetricType.COST.value}

        best_name: str | None = None
        best_score = -1.0

        for pipeline_name, metrics in per_pipeline.items():
            quality_scores = [
                score
                for key, score in metrics.items()
                if key not in _excluded and not key.startswith(MetricType.LATENCY.value)
            ]
            if not quality_scores:
                continue
            mean = sum(quality_scores) / len(quality_scores)
            if mean > best_score:
                best_score = mean
                best_name = pipeline_name

        return best_name
