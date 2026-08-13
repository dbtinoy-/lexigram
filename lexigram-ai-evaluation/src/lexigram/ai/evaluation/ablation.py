"""Ablation runner for the AI evaluation framework.

The :class:`AblationRunner` compares a baseline checkpoint against an
ablated one (a rerun with one configuration knob removed or changed)
and produces per-metric deltas plus a digest-stable result record.
"""

from __future__ import annotations

import hashlib

from lexigram.ai.evaluation.exceptions import AblationError
from lexigram.ai.evaluation.tracking import canonical_json
from lexigram.contracts.ai.experiment import (
    AblationResult,
    CheckpointStoreProtocol,
)
from lexigram.result import Err, Ok, Result

_DIGEST_PREFIX = "ablation-"


class AblationRunner:
    """Compare baseline and ablated checkpoints from a checkpoint store.

    Args:
        store: Checkpoint store holding the baseline and ablated payloads.
    """

    def __init__(self, store: CheckpointStoreProtocol) -> None:
        self._store = store

    @staticmethod
    def deltas(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
        """Compute per-metric deltas (after minus before).

        Args:
            before: Baseline metrics (name to value).
            after: Ablated metrics (name to value).

        Returns:
            Metric name to delta mapping, including keys from either side.
        """
        keys = list(before) + [key for key in after if key not in before]
        return {key: after.get(key, 0.0) - before.get(key, 0.0) for key in keys}

    async def run(
        self,
        run_id: str,
        knob: str,
        baseline_slug: str,
        ablated_slug: str,
    ) -> Result[AblationResult, AblationError]:
        """Compare a baseline checkpoint against an ablated one in one run.

        Args:
            run_id: Run the ablation was performed on.
            knob: The configuration knob that was ablated.
            baseline_slug: Checkpoint slug of the baseline run.
            ablated_slug: Checkpoint slug of the ablated run.

        Returns:
            Ok(AblationResult) with per-metric deltas, or Err(AblationError)
            when either checkpoint is missing.
        """
        return await self.compare(
            knob, run_id, baseline_slug, run_id, ablated_slug
        )

    async def compare(
        self,
        knob: str,
        baseline_run_id: str,
        baseline_slug: str,
        ablated_run_id: str,
        ablated_slug: str,
    ) -> Result[AblationResult, AblationError]:
        """Compare checkpoints across two runs (e.g. control vs ablated).

        Args:
            knob: The configuration knob that was ablated.
            baseline_run_id: Run identifier of the baseline.
            baseline_slug: Checkpoint slug of the baseline run.
            ablated_run_id: Run identifier of the ablated run.
            ablated_slug: Checkpoint slug of the ablated run.

        Returns:
            Ok(AblationResult) with per-metric deltas, or Err(AblationError)
            when either checkpoint is missing.

        Example:
            ```python
            runner = AblationRunner(store)
            result = await runner.compare(
                "thinking",
                "probe-42-a1b2c3d4", "baseline",
                "probe-42-9f8e7d6c", "ablated-thinking",
            )
            ```
        """
        baseline = await self._store.load(baseline_run_id, baseline_slug)
        ablated = await self._store.load(ablated_run_id, ablated_slug)
        if baseline is None or ablated is None:
            missing = baseline_slug if baseline is None else ablated_slug
            return Err(AblationError(f"missing checkpoint {missing!r}"))
        before = {key: float(value) for key, value in baseline.payload.items()}
        after = {key: float(value) for key, value in ablated.payload.items()}
        deltas = self.deltas(before, after)
        digest = hashlib.sha256(
            canonical_json(
                {
                    "knob": knob,
                    "baseline_run_id": baseline_run_id,
                    "baseline": baseline.digest,
                    "ablated_run_id": ablated_run_id,
                    "ablated": ablated.digest,
                    "deltas": deltas,
                }
            ).encode()
        ).hexdigest()
        return Ok(
            AblationResult(
                run_id=baseline_run_id,
                knob=knob,
                baseline_slug=baseline_slug,
                ablated_slug=ablated_slug,
                deltas=deltas,
                digest=f"{_DIGEST_PREFIX}{digest}",
            )
        )


__all__ = ["AblationRunner"]
