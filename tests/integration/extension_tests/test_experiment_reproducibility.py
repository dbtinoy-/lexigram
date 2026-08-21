"""End-to-end reproducibility guarantees of the evaluation subsystem.

Same seed + same inputs must produce identical evaluation totals,
seed-stable run ids, and digest-verified checkpoint round-trips — the
same contract the ``demos/llm-experiment`` harness relies on (see
``docs/ai/EXPERIMENT_REPRODUCIBILITY.md``).
"""

from __future__ import annotations

from pathlib import Path
import random

import pytest

from lexigram.ai.evaluation import (
    EvaluationDataset,
    EvaluationSample,
    FileCheckpointStore,
    make_run_id,
)
from lexigram.ai.evaluation.harness.runner import EvaluationHarness
from lexigram.contracts.ai.evaluation import EvaluationResult, EvaluationScoreType
from lexigram.contracts.core.result import Ok, Result

_SEED = 20260821


class SeededJitterEvaluator:
    """Deterministic evaluator whose scores come from a seeded PRNG.

    A fresh instance replays the exact same score sequence for the same
    seed, mirroring how the experiment harness seeds its payload PRNG.
    """

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    @property
    def name(self) -> str:
        return "seeded_jitter"

    async def evaluate(
        self,
        input: str,
        output: str,
        reference: str,
    ) -> Result[EvaluationResult, Exception]:
        score = round(self._rng.uniform(0.0, 1.0), 6)
        return Ok(
            EvaluationResult(
                score=score,
                score_type=EvaluationScoreType.CUSTOM,
                feedback="seeded",
                metrics={"input_chars": float(len(input))},
            )
        )


def _dataset() -> EvaluationDataset:
    return EvaluationDataset(
        name="reproducibility",
        samples=[
            EvaluationSample(
                id=f"sample-{i}",
                input=f"question-{i}",
                reference=f"answer-{i}",
                metadata={},
            )
            for i in range(12)
        ],
        metadata={},
    )


@pytest.mark.asyncio
async def test_harness_same_seed_identical_run_reports() -> None:
    """Two same-seed harness runs produce identical RunReport totals."""
    dataset = _dataset()
    first = await EvaluationHarness(pass_threshold=0.6).run(
        dataset, SeededJitterEvaluator(_SEED)
    )
    second = await EvaluationHarness(pass_threshold=0.6).run(
        dataset, SeededJitterEvaluator(_SEED)
    )
    assert first.is_ok()
    assert second.is_ok()
    report_a = first.unwrap()
    report_b = second.unwrap()
    assert report_a.total_samples == report_b.total_samples == 12
    assert report_a.passed_samples == report_b.passed_samples
    assert report_a.average_score == report_b.average_score
    assert [r.score for r in report_a.results] == [r.score for r in report_b.results]
    assert report_a.metadata["pass_rate"] == report_b.metadata["pass_rate"]


def test_make_run_id_is_seed_stable() -> None:
    """Run ids derive deterministically from name, seed, and config."""
    variant = {"model": "claude-3-5-sonnet", "_ablate": "control"}
    assert make_run_id("llm-experiment", _SEED, variant) == make_run_id(
        "llm-experiment", _SEED, dict(variant)
    )
    assert make_run_id("llm-experiment", _SEED, variant) != make_run_id(
        "llm-experiment", _SEED + 1, variant
    )


@pytest.mark.asyncio
async def test_checkpoint_roundtrip_preserves_payload_and_digest(
    tmp_path: Path,
) -> None:
    """FileCheckpointStore round-trips payloads digest-verified."""
    store = FileCheckpointStore(root=tmp_path)
    payload = {
        "prompt_tokens": 120.0,
        "completion_tokens": 340.0,
        "cost_dollars": 0.0042,
        "latency_seconds": 0.175042,
    }
    saved = await store.save("run-repro-1", "baseline", payload)
    loaded = await store.load("run-repro-1", "baseline")
    assert loaded is not None
    assert loaded.payload == payload
    assert saved.digest == loaded.digest
