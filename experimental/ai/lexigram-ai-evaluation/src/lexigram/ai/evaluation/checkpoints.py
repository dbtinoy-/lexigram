"""Digest-verified file checkpoints for the AI evaluation framework.

The :class:`FileCheckpointStore` persists run state as JSON documents
under ``<root>/runs/<run_id>/checkpoints/<slug>.json``.  Every payload
is written with a SHA-256 digest of its canonicalized JSON, and loads
re-verify that digest so tampered or corrupted checkpoints are never
returned as valid state.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Any

from lexigram.ai.evaluation.exceptions import CheckpointError
from lexigram.ai.evaluation.tracking import canonical_json
from lexigram.contracts.ai.experiment import Checkpoint, CheckpointStoreProtocol
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str, loads_str

logger = get_logger(__name__)


def _payload_digest(payload: dict[str, Any]) -> str:
    """Return the SHA-256 digest of a canonicalized payload."""
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


class FileCheckpointStore(CheckpointStoreProtocol):
    """Filesystem checkpoint store with digest verification.

    Args:
        root: Base directory for run artifacts. Defaults to ``runs``.
    """

    def __init__(self, root: str | Path = "runs") -> None:
        self._root = Path(root)

    def _checkpoint_file(self, run_id: str, slug: str) -> Path:
        return self._root / "runs" / run_id / "checkpoints" / f"{slug}.json"

    async def save(self, run_id: str, slug: str, payload: dict[str, Any]) -> Checkpoint:
        """Persist a checkpoint for a run.

        Args:
            run_id: Run identifier.
            slug: Stable name of the checkpoint within the run.
            payload: State to checkpoint.

        Returns:
            The stored checkpoint with its content digest.

        Raises:
            CheckpointError: If the checkpoint cannot be written.
        """
        checkpoint = Checkpoint(
            run_id=run_id,
            slug=slug,
            digest=_payload_digest(payload),
            payload=payload,
            created_at=datetime.now(UTC).isoformat(),
        )
        path = self._checkpoint_file(run_id, slug)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                dumps_str(
                    {
                        "run_id": run_id,
                        "slug": slug,
                        "digest": checkpoint.digest,
                        "payload": payload,
                        "created_at": checkpoint.created_at,
                    },
                    sort_keys=True,
                )
            )
        except OSError as exc:
            raise CheckpointError(
                f"cannot write checkpoint {slug!r} for run {run_id!r}: {exc}"
            ) from exc
        return checkpoint

    async def load(self, run_id: str, slug: str) -> Checkpoint | None:
        """Load a checkpoint, verifying its content digest.

        Args:
            run_id: Run identifier.
            slug: Checkpoint name.

        Returns:
            The verified checkpoint, or ``None`` when absent or tampered.
        """
        path = self._checkpoint_file(run_id, slug)
        if not path.exists():
            return None
        try:
            data = loads_str(path.read_text())
        except (OSError, ValueError) as exc:
            raise CheckpointError(
                f"cannot read checkpoint {slug!r} for run {run_id!r}: {exc}"
            ) from exc
        payload = data["payload"]
        expected = data.get("digest", "")
        actual = _payload_digest(payload)
        if actual != expected:
            logger.warning("checkpoint_digest_mismatch", run_id=run_id, slug=slug)
            return None
        return Checkpoint(
            run_id=run_id,
            slug=slug,
            digest=actual,
            payload=payload,
            created_at=data.get("created_at", ""),
        )

    async def list(self, run_id: str) -> list[Checkpoint]:
        """List all checkpoints for a run.

        Args:
            run_id: Run identifier.

        Returns:
            Checkpoints in creation order.
        """
        directory = self._root / "runs" / run_id / "checkpoints"
        if not directory.is_dir():
            return []
        checkpoints: list[Checkpoint] = []
        for path in sorted(directory.glob("*.json")):
            loaded = await self.load(run_id, path.stem)
            if loaded is not None:
                checkpoints.append(loaded)
        return checkpoints


__all__ = ["FileCheckpointStore"]
