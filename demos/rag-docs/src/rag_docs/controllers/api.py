"""REST surface for the rag-docs demo — the **Result-pattern showcase**.

Every handler returns ``Result<Ok, Err>`` instead of raising or returning
raw responses.  The web pipeline then does the boring work:

- ``Ok(payload)``            → serialized as JSON
- ``Err(ValidationError)``   → HTTP 422 ProblemDetail
- ``Err(UnknownStrategyError)`` → HTTP 400
- ``Err(NoResultsError)``    → HTTP 404
- ``Err(SynthesisFailedError)`` → HTTP 502

So handlers read like use-cases ("validate → embed → search → synthesize")
and error-to-HTTP mapping lives in exactly one place.  Compare with the
try/except-and-JSONResponse dance in traditional stacks.

Error mapping is registered once at module level::

    ResultResponseMapper.register(UnknownStrategyError, 400)
    ResultResponseMapper.register(NoResultsError, 404)
    ResultResponseMapper.register(SynthesisFailedError, 502)
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

    Lexigram pattern: controllers are stateless handlers that receive
    collaborators via constructor injection.  The framework resolves the
    controller when a request matches its routes — you never instantiate
    it manually.

    Route decorators (@get, @post) come from lexigram.web, not Starlette
    directly — they integrate with the framework's middleware stack.

    Handlers return the service's ``Result`` directly; the pipeline renders
    ``Ok`` payloads and maps domain errors to ProblemDetail responses using
    the registered status mappings above.
    """

    def __init__(self, service: DocsAskService) -> None:
        self.service = service

    @post("/ask")
    async def ask(
        self,
        request: Request,
    ) -> Result[dict[str, Any], DocsAskError | ValidationError]:
        """Answer a natural-language question with citations.

        Return type uses ``Result[T, E]`` — the web pipeline maps Err
        types to HTTP status codes automatically (ValidationError → 422,
        UnknownStrategyError → 400, NoResultsError → 404,
        SynthesisFailedError → 502).

        Flow: validate → delegate to service → return Ok(answer).
        """
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
        """Return corpus index stats (files/chunks ingested at boot)."""
        stats = self.service.corpus_stats
        return {"files": stats.files, "chunks": stats.chunks}


__all__ = ["DocsAskApiController"]
