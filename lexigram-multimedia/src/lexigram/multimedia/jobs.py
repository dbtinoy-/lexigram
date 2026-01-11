"""Thin wrapper around lexigram-tasks' IdempotencyResult.

Exists so multimedia callers don't need to import lexigram-tasks types
directly — see design spec 'Async job model'.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JobHandle:
    job_id: str
    status: str
    is_duplicate: bool = False

    @classmethod
    def from_idempotency_result(
        cls, result: Any, *, is_duplicate: bool | None = None
    ) -> JobHandle:
        # lexigram-tasks' IdempotencyResult.status is only ever "submitted"
        # or "completed" — despite what IdempotentTaskManager.submit_task()'s
        # own docstring example implies, it never carries a "duplicate"
        # value. A duplicate of a still in-flight ("submitted") submission is
        # therefore indistinguishable from a fresh one using status alone.
        # Callers that can determine duplicate-ness more reliably (see
        # SubsystemAccessor.submit()) should pass is_duplicate explicitly;
        # otherwise fall back to the one unambiguous signal available: a
        # "completed" result can only be a duplicate, since a fresh
        # submission always comes back "submitted".
        if is_duplicate is None:
            is_duplicate = result.status == "completed"
        return cls(
            job_id=result.task_id, status=result.status, is_duplicate=is_duplicate
        )


__all__ = ["JobHandle"]
