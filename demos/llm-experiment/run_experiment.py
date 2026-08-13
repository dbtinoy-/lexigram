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
import logging
import os
from pathlib import Path

from harness import ExperimentResult, metrics_delta, run_experiment

from lexigram.ai.evaluation import AblationRunner, FileCheckpointStore
from lexigram.contracts.ai.experiment import AblationResult

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("lexigram-experiment")

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
    args = parse_args(argv)
    import yaml

    config = yaml.safe_load(args.config.read_text())
    seed = args.seed
    if seed is None:
        env_seed = os.getenv("LEXIGRAM_EXPERIMENT_SEED")
        seed = int(env_seed) if env_seed else int(config["experiment"]["seed"])

    baseline = run_experiment(config, seed=seed, out_dir=args.out, ablate=args.ablate)
    logger.info("run_id=%s digest=%s", baseline.run_id, baseline.digest)
    logger.info(
        "checkpoints=%d traces=%d cost=$%.6f",
        len(baseline.checkpoint_paths),
        len(baseline.trace),
        baseline.result["totals"]["cost_dollars"],
    )

    if args.ablate:
        control = run_experiment(config, seed=seed, out_dir=args.out)
        deltas = metrics_delta(control, baseline)
        logger.info("ablation=%s delta=%s", args.ablate, deltas)
        record = _framework_ablation(control, baseline, args.out, args.ablate)
        logger.info(
            "ablation_record=ok run=%s slugs=%s+%s digest=%s deltas=%s",
            record.run_id,
            record.baseline_slug,
            record.ablated_slug,
            record.digest,
            record.deltas,
        )

    rerun = run_experiment(config, seed=seed, out_dir=args.out, ablate=args.ablate)
    if rerun.digest == baseline.digest:
        logger.info("reproducibility=ok same-seed runs produce an identical digest")
    else:
        logger.error("reproducibility=failed digests diverged")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
