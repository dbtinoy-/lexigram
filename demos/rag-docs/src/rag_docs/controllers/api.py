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

from lexigram.contracts.exceptions.domain import ValidationError
from lexigram.result import Err, Ok, Result
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, get, post
from lexigram.web.routing.result_bridge import ResultResponseMapper
from rag_docs.errors import (
    DocsAskError,
    NoResultsError,
    SynthesisFailedError,
    UnknownStrategyError,
)
from rag_docs.services.docs_ask import DocsAskService

# Domain error → HTTP status mappings (rendered as ProblemDetail bodies).
ResultResponseMapper.register(UnknownStrategyError, 400)
ResultResponseMapper.register(NoResultsError, 404)
ResultResponseMapper.register(SynthesisFailedError, 502)


class DocsAskApiController(Controller):
    """Expose the docs ask service over HTTP.

    Handlers return the service's ``Result`` directly; the pipeline renders
    ``Ok`` payloads and maps domain errors to ProblemDetail responses using
    the registered status mappings below.
    """

    def __init__(self, service: DocsAskService) -> None:
        self.service = service

    @post("/ask")
    async def ask(
        self,
        request: Request,
    ) -> Result[dict[str, Any], DocsAskError | ValidationError]:
        """Answer a natural-language question with citations."""
        body = json_loads(await request.body())
        question = str(body.get("question") or "").strip()
        if not question:
            return Err(ValidationError("question is required"))
        strategy = str(body.get("strategy") or "vector")

        inner = await self.service.ask(question, strategy=strategy)
        if inner.is_err():
            return Err(inner.unwrap_err())
        answer = inner.unwrap()
        return Ok(
            {
                "answer": answer.answer,
                "citations": list(answer.citations),
            },
        )

    @get("/stats")
    async def health(self, request: Request | None = None) -> dict[str, Any]:
        """Return corpus index stats."""
        stats = self.service.corpus_stats
        return {"files": stats.files, "chunks": stats.chunks}


__all__ = ["DocsAskApiController"]
