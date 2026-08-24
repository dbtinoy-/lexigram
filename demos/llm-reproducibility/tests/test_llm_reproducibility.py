"""Tests for the seeded LLM relay experiment harness.

Verifies the reproducibility contract the demo advertises: same seed plus
same config produces a byte-identical digest, a different seed diverges,
and the thinking-ablation path produces a measurable delta.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from llm_reproducibility.results import ExperimentResult, metrics_delta
from llm_reproducibility.runner import run_experiment


def make_config() -> dict[str, Any]:
    """Return a minimal experiment config (mirrors config.yaml)."""
    return {
        "experiment": {
            "name": "llm-relay-probe-test",
            "description": "Deterministic conversion probe (test config)",
            "seed": 42,
            "iterations": 2,
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "tracing_enabled": True,
            "metrics_enabled": True,
        }
    }


def test_same_seed_produces_identical_digest(tmp_path: Path) -> None:
    config = make_config()

    first = run_experiment(config, seed=42, out_dir=tmp_path)
    second = run_experiment(config, seed=42, out_dir=tmp_path)

    assert first.digest == second.digest
    assert first.run_id == second.run_id


def test_different_seed_diverges(tmp_path: Path) -> None:
    config = make_config()

    baseline = run_experiment(config, seed=42, out_dir=tmp_path)
    other = run_experiment(config, seed=43, out_dir=tmp_path)

    assert baseline.digest != other.digest


def test_ablation_changes_digest_and_delta_is_empty_for_identical_runs(
    tmp_path: Path,
) -> None:
    config = make_config()

    control = run_experiment(config, seed=42, out_dir=tmp_path)
    ablated = run_experiment(config, seed=42, out_dir=tmp_path, ablate="thinking")

    # Ablating thinking changes the payloads, so digests must diverge...
    assert control.digest != ablated.digest
    # ...the ablation must move at least one metric...
    ablation_deltas = metrics_delta(control, ablated)
    assert any(value != 0 for value in ablation_deltas.values())
    # ...while an identical rerun yields all-zero deltas.
    rerun_deltas = metrics_delta(control, run_experiment(config, seed=42, out_dir=tmp_path))
    assert rerun_deltas
    assert all(value == 0 for value in rerun_deltas.values())


def test_artifacts_land_under_runs_directory(tmp_path: Path) -> None:
    result = run_experiment(make_config(), seed=42, out_dir=tmp_path)

    run_dir = tmp_path / "runs" / result.run_id
    assert run_dir.is_dir()
    assert len(result.checkpoint_paths) > 0
