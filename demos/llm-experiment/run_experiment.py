"""Run the seeded LLM relay experiment from the command line.

Usage:
    python run_experiment.py --seed 42
    python run_experiment.py --seed 42 --ablate thinking
    LEXIGRAM_EXPERIMENT_SEED=7 python run_experiment.py

The reproducibility path is simple: same config + same seed -> same
run_id and same digest. Artifacts land under ``runs/<run_id>/``.
Ablation runs additionally write a digest-verified delta record via
:class:`~lexigram.ai.evaluation.AblationRunner`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from experiment.results import ExperimentResult, metrics_delta
from experiment.runner import run_experiment

from lexigram.ai.evaluation import AblationRunner, FileCheckpointStore
from lexigram.contracts.ai.experiment import AblationResult
from lexigram.logging import configure_logging, get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG = Path(__file__).parent / "experiment.yaml"
DEFAULT_OUT = Path(__file__).parent / "runs"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--ablate", choices=["thinking"], default=None)
    return parser.parse_args(argv)


def _framework_ablation(
    control: ExperimentResult, ablated: ExperimentResult, out_dir: Path, knob: str
) -> AblationResult:
    """Persist a framework ablation-delta record between two runs."""

    async def _go() -> AblationResult:
        runner = AblationRunner(FileCheckpointStore(root=out_dir))
        result = await runner.compare(
            knob=knob,
            baseline_run_id=control.run_id,
            baseline_slug="baseline",
            ablated_run_id=ablated.run_id,
            ablated_slug=f"ablated-{knob}",
        )
        if result.is_err():
            raise RuntimeError(f"ablation compare failed: {result.unwrap_err()}")
        return result.unwrap()

    return asyncio.run(_go())


def main(argv: list[str] | None = None) -> int:
    """Execute the experiment and print the reproducibility digest."""
    configure_logging(level="INFO")
    args = parse_args(argv)
    import yaml

    config = yaml.safe_load(args.config.read_text())
    seed = args.seed
    if seed is None:
        env_seed = os.getenv("LEXIGRAM_EXPERIMENT_SEED")
        seed = int(env_seed) if env_seed else int(config["experiment"]["seed"])

    baseline = run_experiment(config, seed=seed, out_dir=args.out, ablate=args.ablate)
    logger.info(
        "experiment_run_complete",
        run_id=baseline.run_id,
        digest=baseline.digest,
    )
    logger.info(
        "experiment_stats",
        checkpoints=len(baseline.checkpoint_paths),
        traces=len(baseline.trace),
        cost_dollars=baseline.result["totals"]["cost_dollars"],
    )

    if args.ablate:
        control = run_experiment(config, seed=seed, out_dir=args.out)
        deltas = metrics_delta(control, baseline)
        logger.info("experiment_ablation", knob=args.ablate, delta=deltas)
        record = _framework_ablation(control, baseline, args.out, args.ablate)
        logger.info(
            "ablation_record_ok",
            run_id=record.run_id,
            slugs=f"{record.baseline_slug}+{record.ablated_slug}",
            digest=record.digest,
            deltas=record.deltas,
        )

    rerun = run_experiment(config, seed=seed, out_dir=args.out, ablate=args.ablate)
    if rerun.digest == baseline.digest:
        logger.info("reproducibility_ok")
    else:
        logger.error(
            "reproducibility_failed",
            baseline_digest=baseline.digest,
            rerun_digest=rerun.digest,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
