"""JSON API for the memory-chat console — no HTML lives here."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request

from lexigram.contracts.exceptions.domain import ValidationError
from lexigram.result import Err, Ok, Result
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, JSONResponse, get, post
from memory_chat.services.chat_service import ConciergeService


async def _body(request: Request) -> dict[str, Any]:
    """Parse the request body through the framework serializer."""
    raw = await request.body()
    if not raw:
        return {}
    parsed = json_loads(raw)
    return dict(parsed) if isinstance(parsed, dict) else {}


class ConciergeApiController(Controller):
    """Endpoints consumed by ui/static/app.js."""

    def __init__(self, concierge: ConciergeService) -> None:
        self._concierge = concierge

    @post("/api/chat")
    async def chat(self, request: Request) -> Result[dict, ValidationError]:
        """One conversational turn for an owner."""
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
        """Snapshot of everything stored about one owner."""
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
        """Scripted two-session replay proving recall and isolation."""
        result = await self._concierge.demo_replay()
        return JSONResponse(
            {
                "transcript": result.transcript,
                "isolation_ok": result.isolation_ok,
            },
        )


__all__ = ["ConciergeApiController"]
