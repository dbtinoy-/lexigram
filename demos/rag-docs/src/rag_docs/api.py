"""REST surface for the rag-docs demo.

- ``POST /ask``  — ``{"question": str, "strategy": "vector"|"mmr"}`` →
  ``{"answer": str, "citations": [chunk-id, ...]}``
- ``GET /stats`` — index stats (files/chunks ingested at boot).

Errors map to status codes: unknown strategy → 400, nothing retrieved →
404, synthesis failure → 502.
"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.web import Controller, get, post
from rag_docs.errors import (
    NoResultsError,
    SynthesisFailedError,
    UnknownStrategyError,
)
from rag_docs.services.docs_ask import DocsAskService


class DocsAskApiController(Controller):
    """Expose the docs ask service over HTTP."""

    def __init__(self, service: DocsAskService) -> None:
        self.service = service

    @post("/ask")
    async def ask(self, request: Request) -> JSONResponse:
        """Answer a natural-language question with citations."""
        body = await request.json()
        question = str(body.get("question") or "").strip()
        if not question:
            return JSONResponse({"error": "question is required"}, status_code=400)
        strategy = str(body.get("strategy") or "vector")

        result = await self.service.ask(question, strategy=strategy)
        if result.is_err():
            error = result.unwrap_err()
            return JSONResponse(
                {"error": str(error)},
                status_code=_STATUS_BY_ERROR.get(type(error), 502),
            )
        answer = result.unwrap()
        return JSONResponse(
            {"answer": answer.answer, "citations": list(answer.citations)}
        )

    @get("/stats")
    async def health(self, request: Request | None = None) -> dict[str, Any]:
        """Return corpus index stats."""
        stats = self.service.corpus_stats
        return {"files": stats.files, "chunks": stats.chunks}


_STATUS_BY_ERROR: dict[type[Exception], int] = {
    UnknownStrategyError: 400,
    NoResultsError: 404,
    SynthesisFailedError: 502,
}


__all__ = ["DocsAskApiController"]
