"""Run the seeded LLM relay experiment from the command line.

Usage:
    python run_experiment.py --seed 42
    python run_experiment.py --seed 42 --ablate thinking
    LEXIGRAM_EXPERIMENT_SEED=7 python run_experiment.py

The reproducibility path is simple: same config + same seed -> same
run_id and same digest. Artifacts land under ``runs/<run_id>/``.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from harness import metrics_delta, run_experiment

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

    rerun = run_experiment(config, seed=seed, out_dir=args.out, ablate=args.ablate)
    if rerun.digest == baseline.digest:
        logger.info("reproducibility=ok same-seed runs produce an identical digest")
    else:
        logger.error("reproducibility=failed digests diverged")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())