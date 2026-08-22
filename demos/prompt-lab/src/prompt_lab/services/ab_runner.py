"""Render → respond → evaluate → compare, fully offline."""

from __future__ import annotations

from dataclasses import dataclass, field

from prompt_lab.repository.cases import CASES, CRITERIA

from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator
from lexigram.ai.evaluation.harness.runner import EvaluationHarness
from lexigram.contracts.ai.evaluation import EvaluationDataset
from lexigram.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ScoredSample:
    """Mirrors ``EvaluationSample`` plus ``output`` (runner duck-types it)."""

    id: str
    input: str
    output: str
    reference: str
    metadata: dict = field(default_factory=dict)


class ABRunner:
    """Scores both variants over CASES via ``CriteriaEvaluator``."""

    def __init__(
        self,
        versions,
        harness: EvaluationHarness | None = None,
    ) -> None:
        self._versions = versions
        self._harness = harness or EvaluationHarness(pass_threshold=0.8)

    async def run_all(self) -> dict:
        """Score every variant over all cases; return totals + winner."""
        evaluator = CriteriaEvaluator(criteria=CRITERIA)
        variants_report: dict[str, dict] = {}
        for variant in ("v1", "v2"):
            _rev, template = self._versions.active(variant)
            samples = [
                ScoredSample(
                    id=case.id,
                    input=template.render_as_string(
                        issue=case.question,
                        tone="neutral",
                    ),
                    output=_responder(variant)(case.question),
                    reference=case.reference,
                    metadata={},
                )
                for case in CASES
            ]
            dataset = EvaluationDataset(
                name=f"ab-{variant}",
                samples=list(samples),
                metadata={},
            )
            result = await self._harness.run(dataset, evaluator)
            if result.is_err():
                raise RuntimeError(f"harness failed: {result.unwrap_err()}")
            report = result.unwrap()
            passed = sum(
                1
                for r in report.results
                if r.score >= report.metadata["pass_threshold"]
            )
            variants_report[variant] = {
                "average_score": round(report.average_score, 4),
                "passed": passed,
                "total": report.total_samples,
            }
        winner = max(
            variants_report,
            key=lambda k: variants_report[k]["average_score"],
        )
        logger.info(
            "ab_run_complete",
            winner=winner,
            scores={k: v["average_score"] for k, v in variants_report.items()},
        )
        return {"variants": variants_report, "winner": winner}


def _responder(variant: str):
    """Late-bound responder lookup (keeps import surface minimal)."""
    from prompt_lab.repository.responders import RESPONDERS

    responder = RESPONDERS.get(variant)
    if responder is None:
        raise KeyError(f"no responder for variant {variant!r}")
    return responder
