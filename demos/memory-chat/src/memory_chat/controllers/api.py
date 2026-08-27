"""JSON API for the memory-chat console — the **Result-pattern showcase**.

Every handler returns ``Result<Ok, Err>`` instead of raising or returning
raw responses.  The web pipeline then does the boring work:

- ``Ok(payload)``            → serialized as JSON (or rendered)
- ``Err(ValidationError)``   → HTTP 422 ProblemDetail

So handlers read like use-cases ("record → extract → recall → respond")
and error-to-HTTP mapping lives in exactly one place.  Compare with the
try/except-and-JSONResponse dance in traditional stacks.

Memory flow across these endpoints: each ``/api/chat`` turn records the
entry to episodic memory, extracts facts into semantic memory, recalls
relevant context, and renders a deterministic reply — no LLM involved.
The ``/api/facts/{owner}`` endpoint snapshots everything stored about one
owner, and ``/api/demo`` replays a scripted two-session story proving
recall and cross-owner isolation.
"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request

from lexigram.contracts.exceptions.domain import ValidationError
from lexigram.result import Err, Ok, Result
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, JSONResponse, get, post
from memory_chat.services.chat_service import ConciergeService


async def _body(request: Request) -> dict[str, Any]:
    """Parse the request body through the framework serializer.

    ``json_loads`` handles content negotiation and encoding; this helper
    keeps every handler free of boilerplate body-parsing.
    """
    raw = await request.body()
    if not raw:
        return {}
    parsed = json_loads(raw)
    return dict(parsed) if isinstance(parsed, dict) else {}


class ConciergeApiController(Controller):
    """Endpoints consumed by ui/static/app.js.

    Lexigram pattern: controllers are stateless handlers that receive
    collaborators via constructor injection.  The framework resolves the
    controller when a request matches its routes — you never instantiate
    it manually.

    Route decorators (@get, @post) come from lexigram.web, not Starlette
    directly — they integrate with the framework's middleware stack.
    """

    def __init__(self, concierge: ConciergeService) -> None:
        self._concierge = concierge

    @post("/api/chat")
    async def chat(self, request: Request) -> Result[dict, ValidationError]:
        """One conversational turn for an owner.

        Return type uses ``Result[T, E]`` — the web pipeline maps Err
        types to HTTP status codes automatically (ValidationError → 422).

        Flow: validate → record → extract facts → recall context → respond.
        """
        data = await _body(request)
        owner = str(data.get("owner", "")).strip()
        text = str(data.get("text", ""))
        if not owner or not text.strip():
            return Err(ValidationError("owner and text are required"))

        inner = await self._concierge.send(owner, text)
        if inner.is_err():
            return Err(inner.unwrap_err())
        turn = inner.unwrap()
        return Ok(
            {
                "reply": turn.reply_text,
                "cited": turn.cited,
                "context_chars": turn.context_chars,
            },
        )

    @get("/api/facts/{owner}")
    async def facts(self, request: Request) -> JSONResponse:
        """Snapshot of everything stored about one owner.

        Returns semantic triples (subject/predicate/object) and recent
        episodic entries — the two memory tiers the demo Demonstrates.
        """
        snapshot = await self._concierge.get_facts(request.path_params["owner"])
        return JSONResponse(
            {
                "triples": snapshot.triples,
                "recent": [
                    {"content": e.content, "role": e.role} for e in snapshot.recent
                ],
            },
        )

    @post("/api/demo")
    async def demo(self, request: Request) -> JSONResponse:
        """Scripted two-session replay proving recall and isolation.

        Runs alice (diet + allergy → menu) then bob (no facts → "anything
        goes").  The ``isolation_ok`` flag confirms bob never sees alice's
        facts — the core teaching point of this demo.
        """
        result = await self._concierge.demo_replay()
        return JSONResponse(
            {
                "transcript": result.transcript,
                "isolation_ok": result.isolation_ok,
            },
        )


__all__ = ["ConciergeApiController"]
