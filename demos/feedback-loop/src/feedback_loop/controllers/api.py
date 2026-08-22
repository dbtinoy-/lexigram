"""JSON API for the feedback-loop console — no HTML lives here.

Handlers return ``Result`` values; the web pipeline renders ``Ok`` payloads
and maps ``Err`` errors to ProblemDetail responses automatically (the demo's
domain errors subclass contracts' NotFound/Validation/Conflict errors).
"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request

from feedback_loop.services.loop_service import LoopService
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, get, post


async def _body(request: Request) -> dict[str, Any]:
    """Parse the request body through the framework serializer."""
    raw = await request.body()
    if not raw:
        return {}
    parsed = json_loads(raw)
    return dict(parsed) if isinstance(parsed, dict) else {}


class LoopApiController(Controller):
    """Endpoints consumed by ui/static/app.js."""

    def __init__(self, service: LoopService) -> None:
        self._service = service

    @post("/api/ask")
    async def ask(self, request: Request) -> Result[dict, Exception]:
        """Answer a canned question, issuing its stable trace id."""
        data = await _body(request)
        key = str(data.get("key", ""))
        owner = str(data.get("owner", "")).strip()

        result = await self._service.ask(key, owner=owner or "web-user")
        return result.map_sync(
            lambda answer: {
                "trace_id": answer.trace_id,
                "question": answer.question,
                "answer": answer.answer,
            },
        )

    @post("/api/rate")
    async def rate(
        self,
        request: Request,
    ) -> Result[dict, Exception]:
        """Capture a 1..5 rating for a previously issued trace id."""
        data = await _body(request)
        trace_id = str(data.get("trace_id", ""))
        owner = str(data.get("owner", "")).strip()
        comment = str(data.get("comment", "")) or None
        try:
            rating = float(data.get("rating", 0))
        except (TypeError, ValueError):
            rating = float("nan")  # out of bounds ⇒ InvalidRatingError path

        result = await self._service.rate(
            trace_id,
            rating,
            owner=owner or "web-user",
            comment=comment,
        )
        return result.map_sync(lambda item_id: {"item_id": item_id})

    @get("/api/stats/{owner}")
    async def stats(self, request: Request) -> dict:
        """Aggregate this owner's captured ratings."""
        snap = await self._service.stats(owner=request.path_params["owner"])
        avg = snap.average if snap.average is not None else "n/a"
        return {"total": snap.total, "average": avg, "by_type": snap.by_type}

    @post("/api/regress")
    async def regress(self, request: Request) -> Result[dict, Exception]:
        """Promote low-rated exchanges into a tracked regression run."""
        data = await _body(request)
        owner = str(data.get("owner", "")).strip() or "web-user"

        result = await self._service.regress(owner=owner)
        return result.map_sync(
            lambda summary: {
                "run_id": summary.run_id,
                "total_samples": summary.total_samples,
                "passed_samples": summary.passed_samples,
                "average_score": summary.average_score,
                "failing_ids": summary.failing_ids,
            },
        )

    @get("/api/report/{run_id}")
    async def report(self, request: Request) -> dict:
        """Post-hoc error analysis for a tracked run."""
        run_id = request.path_params["run_id"]
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
