"""Seed-stable local experiment tracking for the AI evaluation framework.

The :class:`LocalTracker` persists runs as JSON documents plus JSONL
metric/error streams under ``<root>/runs/<run_id>/``.  Run ids are
derived deterministically from the experiment name, seed, and
canonicalized knob config, so rerunning the same seed and knobs resumes
the same run and produces byte-identical artifacts.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Any

from lexigram.ai.evaluation.exceptions import TrackingError
from lexigram.contracts.ai.experiment import (
    ErrorRecord,
    ExperimentConfig,
    ExperimentRun,
    ExperimentTrackerProtocol,
    MetricRecord,
    RunStatus,
)
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str, loads_str

logger = get_logger(__name__)


def canonical_json(data: Any) -> str:
    """Serialize ``data`` to a stable, key-sorted JSON string."""
    return dumps_str(data, sort_keys=True)


def make_run_id(name: str, seed: int, config: dict[str, Any]) -> str:
    """Derive a deterministic run id from name, seed, and canonical config.

    Args:
        name: Experiment name.
        seed: Seed value.
        config: Knob configuration dict.

    Returns:
        Run id of the form ``<name>-<seed>-<8-char digest>``.

    Example:
        ```python
        run_id = make_run_id("probe", 42, {"model": "gpt-4o"})
        assert run_id == make_run_id("probe", 42, {"model": "gpt-4o"})
        ```
    """
    digest = hashlib.sha256(
        f"{name}|{seed}|{canonical_json(config)}".encode()
    ).hexdigest()[:8]
    return f"{name}-{seed}-{digest}"


class LocalTracker(ExperimentTrackerProtocol):
    """JSON/JSONL-backed tracker persisting runs under ``<root>/runs/``.

    Args:
        root: Base directory for run artifacts. Defaults to ``runs``.
    """

    def __init__(self, root: str | Path = "runs") -> None:
        self._root = Path(root)

    def _run_dir(self, run_id: str) -> Path:
        return self._root / "runs" / run_id

    def _load_run(self, run_id: str) -> ExperimentRun | None:
        run_file = self._run_dir(run_id) / "run.json"
        if not run_file.exists():
            return None
        try:
            data = loads_str(run_file.read_text())
        except (OSError, ValueError) as exc:
            raise TrackingError(f"cannot read run {run_id!r}: {exc}") from exc
        return ExperimentRun(
            **{key: value for key, value in data.items() if key != "status"},
            status=RunStatus(data["status"]),
        )

    def _store_run(self, run: ExperimentRun) -> ExperimentRun:
        run_file = self._run_dir(run.run_id) / "run.json"
        try:
            run_file.write_text(
                dumps_str(
                    {
                        "run_id": run.run_id,
                        "experiment": run.experiment,
                        "seed": run.seed,
                        "config": run.config,
                        "config_hash": run.config_hash,
                        "status": run.status.value,
                        "started_at": run.started_at,
                        "finished_at": run.finished_at,
                    },
                    sort_keys=True,
                )
            )
        except OSError as exc:
            raise TrackingError(f"cannot persist run {run.run_id!r}: {exc}") from exc
        return run

    async def start(self, config: ExperimentConfig) -> ExperimentRun:
        """Start (or resume) an experiment run for the given config.

        Args:
            config: Seed and knob configuration of the run.

        Returns:
            The started or resumed run.

        Raises:
            TrackingError: If the run manifest cannot be persisted.
        """
        run_id = make_run_id(config.name, config.seed, config.config)
        existing = self._load_run(run_id)
        if existing is not None:
            return existing
        self._run_dir(run_id).mkdir(parents=True, exist_ok=True)
        run = ExperimentRun(
            run_id=run_id,
            experiment=config.name,
            seed=config.seed,
            config=config.config,
            config_hash=hashlib.sha256(
                canonical_json(config.config).encode()
            ).hexdigest(),
            status=RunStatus.RUNNING,
            started_at=datetime.now(UTC).isoformat(),
        )
        self._store_run(run)
        return run

    async def log_metric(
        self, run_id: str, name: str, value: float, step: int = 0
    ) -> None:
        """Record a scalar metric for a run.

        Args:
            run_id: Run identifier.
            name: Metric name.
            value: Metric value.
            step: Step index the metric was recorded at. Defaults to 0.

        Raises:
            TrackingError: If the metric line cannot be appended.
        """
        self._append(
            run_id, "metrics.jsonl", {"step": step, "name": name, "value": value}
        )

    async def log_error(
        self, run_id: str, kind: str, message: str, step: int = 0
    ) -> None:
        """Record an error for a run.

        Args:
            run_id: Run identifier.
            kind: Error kind or code.
            message: Human-readable error message.
            step: Step index the error occurred at. Defaults to 0.

        Raises:
            TrackingError: If the error line cannot be appended.
        """
        self._append(
            run_id, "errors.jsonl", {"kind": kind, "message": message, "step": step}
        )

    def _append(self, run_id: str, filename: str, record: dict[str, Any]) -> None:
        stream = self._run_dir(run_id) / filename
        try:
            stream.parent.mkdir(parents=True, exist_ok=True)
            with stream.open("a") as handle:
                handle.write(canonical_json(record) + "\n")
        except OSError as exc:
            raise TrackingError(
                f"cannot append {filename} for run {run_id!r}: {exc}"
            ) from exc

    async def metrics(self, run_id: str) -> list[MetricRecord]:
        """Return all metric records for a run.

        Args:
            run_id: Run identifier.

        Returns:
            Metric records in recording order.
        """
        return [MetricRecord(**line) for line in self._stream(run_id, "metrics.jsonl")]

    async def errors(self, run_id: str) -> list[ErrorRecord]:
        """Return all error records for a run.

        Args:
            run_id: Run identifier.

        Returns:
            Error records in recording order.
        """
        return [ErrorRecord(**line) for line in self._stream(run_id, "errors.jsonl")]

    def _stream(self, run_id: str, filename: str) -> list[dict[str, Any]]:
        stream = self._run_dir(run_id) / filename
        if not stream.exists():
            return []
        try:
            return [
                loads_str(line)
                for line in stream.read_text().splitlines()
                if line.strip()
            ]
        except (OSError, ValueError) as exc:
            raise TrackingError(
                f"cannot read {filename} for run {run_id!r}: {exc}"
            ) from exc

    async def snapshot(self, run_id: str) -> dict[str, Any]:
        """Return a compact summary of a run's current state.

        Args:
            run_id: Run identifier.

        Returns:
            Latest value per metric, error counts, and run metadata.

        Raises:
            TrackingError: If the run is unknown.
        """
        run = self._load_run(run_id)
        if run is None:
            raise TrackingError(f"unknown run {run_id!r}")
        latest: dict[str, float] = {}
        for metric in await self.metrics(run_id):
            latest[metric.name] = metric.value
        kinds: dict[str, int] = {}
        for error in await self.errors(run_id):
            kinds[error.kind] = kinds.get(error.kind, 0) + 1
        return {
            "run_id": run_id,
            "experiment": run.experiment,
            "seed": run.seed,
            "config_hash": run.config_hash,
            "status": run.status.value,
            "metrics": latest,
            "error_kinds": kinds,
        }

    async def resume(self, run_id: str) -> ExperimentRun | None:
        """Return an already-started run, or ``None`` when unknown.

        Args:
            run_id: Run identifier.

        Returns:
            The existing run, or ``None``.
        """
        return self._load_run(run_id)

    async def finish(
        self, run_id: str, status: RunStatus = RunStatus.COMPLETED
    ) -> None:
        """Mark a run finished.

        Args:
            run_id: Run identifier.
            status: Terminal status. Defaults to ``COMPLETED``.

        Raises:
            TrackingError: If the run is unknown.
        """
        run = self._load_run(run_id)
        if run is None:
            raise TrackingError(f"unknown run {run_id!r}")
        finished = self._store_run(
            ExperimentRun(
                run_id=run.run_id,
                experiment=run.experiment,
                seed=run.seed,
                config=run.config,
                config_hash=run.config_hash,
                status=status,
                started_at=run.started_at,
                finished_at=datetime.now(UTC).isoformat(),
            )
        )
        logger.info(
            "experiment_finished", run_id=run_id, status=status.value, finished=finished
        )


__all__ = ["LocalTracker", "canonical_json", "make_run_id"]
