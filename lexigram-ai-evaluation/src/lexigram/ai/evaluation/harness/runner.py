"""Evaluation harness for running evaluators on datasets."""

from __future__ import annotations

from lexigram.contracts.ai.evaluation import (
    EvaluationDataset,
    EvaluationHarnessProtocol,
    EvaluationResult,
    EvaluationScoreType,
    EvaluatorProtocol,
    RunReport,
)
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


class EvaluationHarness(EvaluationHarnessProtocol):
    """Default evaluation harness implementation.

    Runs an evaluator against a dataset and produces a run report.
    """

    def __init__(self, pass_threshold: float = 0.8) -> None:
        self._pass_threshold = pass_threshold

    @property
    def name(self) -> str:
        return "evaluation_harness"

    async def run(
        self,
        dataset: EvaluationDataset,
        evaluator: EvaluatorProtocol,
    ) -> Result[RunReport, Exception]:
        results: list[EvaluationResult] = []
        passed = 0

        logger.info(
            "evaluation_run_started",
            dataset=dataset.name,
            samples=len(dataset.samples),
            evaluator=evaluator.name,
        )

        try:
            for sample in dataset.samples:
                result = await evaluator.evaluate(
                    sample.input,
                    sample.output if hasattr(sample, "output") else "",
                    sample.reference,
                )

                if result.is_ok():
                    eval_result = result.unwrap()
                    results.append(eval_result)
                    if eval_result.score >= self._pass_threshold:
                        passed += 1
                else:
                    error = result.unwrap_err()
                    logger.warning(
                        "sample_evaluation_failed",
                        sample_id=sample.id,
                        error=str(error),
                    )
                    results.append(
                        EvaluationResult(
                            score=0.0,
                            score_type=EvaluationScoreType.CUSTOM,
                            feedback=f"Error: {error}",
                            metrics={"error": str(error)},
                        )
                    )

            total = len(results)
            average = sum(r.score for r in results) / total if total > 0 else 0.0

            report = RunReport(
                dataset_name=dataset.name,
                evaluator_name=evaluator.name,
                total_samples=total,
                passed_samples=passed,
                average_score=average,
                results=results,
                metadata={
                    "pass_threshold": self._pass_threshold,
                    "pass_rate": passed / total if total > 0 else 0.0,
                },
            )

            logger.info(
                "evaluation_run_completed",
                dataset=dataset.name,
                total=total,
                passed=passed,
                average_score=average,
            )

            return Ok(report)
        except Exception as e:
            logger.error(
                "evaluation_run_failed",
                dataset=dataset.name,
                error=str(e),
            )
            return Err(e)


__all__ = ["EvaluationHarness"]
