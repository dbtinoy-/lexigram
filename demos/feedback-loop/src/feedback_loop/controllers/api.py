"""JSON API for the feedback-loop console — no HTML lives here.

Three framework features on display:

- POST handlers take declarative ``DomainModel`` request DTOs — the pipeline
  deserializes and validates the JSON body before the handler runs, so a
  malformed payload answers 422 without touching demo code.
- GET handlers declare path parameters as plain typed arguments; the binder
  resolves them from the route pattern (no ``request.path_params`` digging).
- All mutating handlers return ``Result`` values; the pipeline renders ``Ok``
  payloads and maps ``Err`` errors to ProblemDetail responses automatically
  (the demo's domain errors subclass contracts' NotFound/Validation/Conflict).
"""

from __future__ import annotations

from feedback_loop.errors import (
    InvalidRatingError,
    NoLowRatedError,
    UnknownQuestionError,
    UnknownTraceError,
)
from feedback_loop.schemas import AskRequest, RateRequest, RegressRequest
from feedback_loop.services.loop_service import LoopService
from lexigram.result import Err, Ok, Result
from lexigram.web import Controller, get, post


class LoopApiController(Controller):
    """Endpoints consumed by ui/static/app.js."""

    def __init__(self, service: LoopService) -> None:
        self._service = service

    @post("/api/ask")
    async def ask(
        self,
        payload: AskRequest,
    ) -> Result[dict, UnknownQuestionError]:
        """Answer a canned question, issuing its stable trace id."""
        inner = await self._service.ask(payload.key, owner=payload.owner)
        if inner.is_err():
            return Err(inner.unwrap_err())
        answer = inner.unwrap()
        return Ok(
            {
                "trace_id": answer.trace_id,
                "question": answer.question,
                "answer": answer.answer,
            },
        )

    @post("/api/rate")
    async def rate(
        self,
        payload: RateRequest,
    ) -> Result[dict, UnknownTraceError | InvalidRatingError]:
        """Capture a rating for a previously issued trace id."""
        inner = await self._service.rate(
            payload.trace_id,
            payload.rating,
            owner=payload.owner,
            comment=payload.comment,
        )
        if inner.is_err():
            return Err(inner.unwrap_err())
        return Ok({"item_id": inner.unwrap()})

    @get("/api/stats/{owner}")
    async def stats(self, owner: str) -> dict:
        """Aggregate this owner's captured ratings."""
        snap = await self._service.stats(owner=owner)
        avg = snap.average if snap.average is not None else "n/a"
        return {"total": snap.total, "average": avg, "by_type": snap.by_type}

    @post("/api/regress")
    async def regress(
        self,
        payload: RegressRequest,
    ) -> Result[dict, NoLowRatedError]:
        """Promote low-rated exchanges into a tracked regression run."""
        inner = await self._service.regress(owner=payload.owner)
        if inner.is_err():
            return Err(inner.unwrap_err())
        summary = inner.unwrap()
        return Ok(
            {
                "run_id": summary.run_id,
                "total_samples": summary.total_samples,
                "passed_samples": summary.passed_samples,
                "average_score": summary.average_score,
                "failing_ids": summary.failing_ids,
            },
        )

    @get("/api/report/{run_id}")
    async def report(self, run_id: str) -> dict:
        """Post-hoc error analysis for a tracked run."""
        analysis = await self._service.report(run_id)
        return {
            "run_id": run_id,
            "total_records": analysis.total_records,
            "error_count": analysis.error_count,
            "score_mean": analysis.score_mean,
            "score_min": analysis.score_min,
            "score_max": analysis.score_max,
        }


__all__ = ["LoopApiController"]
