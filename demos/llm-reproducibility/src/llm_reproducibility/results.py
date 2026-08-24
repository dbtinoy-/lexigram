"""Experiment result model, canonical hashing, and delta computation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.serialization import dumps_str


@dataclass(frozen=True)
class ExperimentResult:
    """One fully reproducible experiment run."""

    run_id: str
    params: dict[str, Any]
    metrics: dict[str, Any]
    result: dict[str, Any]
    trace: list[dict[str, str | dict[str, Any]]]
    checkpoint_paths: list[str]
    analysis: dict[str, Any]
    digest: str


def _canonical(value: Any) -> str:
    """Stable, key-sorted JSON serialization for digesting."""
    return dumps_str(value, sort_keys=True)


def metrics_delta(run_a: ExperimentResult, run_b: ExperimentResult) -> dict[str, Any]:
    """Return the metrics delta between two runs for ablation analysis.

    Args:
        run_a: Baseline run (e.g. full feature set).
        run_b: Ablated run (e.g. thinking blocks dropped).

    Returns:
        Per-metric counter deltas and histogram observation count deltas.
    """
    deltas: dict[str, Any] = {}
    for name, series in run_a.metrics["counters"].items():
        baseline = sum(series.values())
        other = run_b.metrics["counters"].get(name, {})
        deltas[name] = round(sum(other.values()) - baseline, 6)
    for name, series in run_a.metrics["histograms"].items():
        baseline = sum(len(v) for v in series.values())
        other = run_b.metrics["histograms"].get(name, {})
        deltas[name] = sum(len(v) for v in other.values()) - baseline
    return deltas


__all__ = ["ExperimentResult", "metrics_delta"]
