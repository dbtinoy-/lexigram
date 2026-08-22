"""JSON API for the feedback-loop console — no HTML lives here."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from feedback_loop.services.loop_service import LoopService
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, get, post


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


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
    async def ask(self, request: Request) -> JSONResponse:
        data = await _body(request)
        key = str(data.get("key", ""))
        owner = str(data.get("owner", "")).strip()
        result = await self._service.ask(key, owner=owner or "web-user")
        if result.is_err():
            return _error(str(result.unwrap_err()), 400)
        answer = result.unwrap()
        return JSONResponse(
            {
                "trace_id": answer.trace_id,
                "question": answer.question,
                "answer": answer.answer,
            },
        )

    @post("/api/rate")
    async def rate(self, request: Request) -> JSONResponse:
        data = await _body(request)
        trace_id = str(data.get("trace_id", ""))
        try:
            rating = float(data.get("rating", 0))
        except (TypeError, ValueError):
            return _error("rating must be a number", 400)
        owner = str(data.get("owner", "")).strip()
        comment = str(data.get("comment", "")) or None

        result = await self._service.rate(
            trace_id,
            rating,
            owner=owner or "web-user",
            comment=comment,
        )
        if result.is_err():
            return _error(str(result.unwrap_err()), 400)
        return JSONResponse({"item_id": result.unwrap()})

    @get("/api/stats/{owner}")
    async def stats(self, request: Request) -> JSONResponse:
        snap = await self._service.stats(owner=request.path_params["owner"])
        avg = snap.average if snap.average is not None else "n/a"
        return JSONResponse(
            {"total": snap.total, "average": avg, "by_type": snap.by_type},
        )

    @post("/api/regress")
    async def regress(self, request: Request) -> JSONResponse:
        data = await _body(request)
        owner = str(data.get("owner", "")).strip() or "web-user"
        result = await self._service.regress(owner=owner)
        if result.is_err():
            return _error(str(result.unwrap_err()), 400)
        summary = result.unwrap()
        return JSONResponse(
            {
                "run_id": summary.run_id,
                "total_samples": summary.total_samples,
                "passed_samples": summary.passed_samples,
                "average_score": summary.average_score,
                "failing_ids": summary.failing_ids,
            },
        )

    @get("/api/report/{run_id}")
    async def report(self, request: Request) -> JSONResponse:
        run_id = request.path_params["run_id"]
        analysis = await self._service.report(run_id)
        return JSONResponse(
            {
                "run_id": run_id,
                "total_records": analysis.total_records,
                "error_count": analysis.error_count,
                "score_mean": analysis.score_mean,
                "score_min": analysis.score_min,
                "score_max": analysis.score_max,
            },
        )


__all__ = ["LoopApiController"]
