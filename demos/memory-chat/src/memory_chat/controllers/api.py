"""JSON API for the memory-chat console — no HTML lives here."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.web import Controller, get, post

from memory_chat.chat_service import ConciergeService


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


class ConciergeApiController(Controller):
    """Endpoints consumed by ui/static/app.js."""

    def __init__(self, concierge: ConciergeService) -> None:
        self._concierge = concierge

    @post("/api/chat")
    async def chat(self, request: Request) -> JSONResponse:
        """One conversational turn for an owner."""
        data = await request.json()
        owner = str(data.get("owner", "")).strip()
        text = str(data.get("text", "")).strip()
        if not owner or not text:
            return _error("owner and text are required", 400)

        result = await self._concierge.send(owner, text)
        return JSONResponse(
            {
                "reply": result.reply_text,
                "cited": result.cited,
                "context_chars": result.context_chars,
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
                    {"content": e.content, "role": e.role}
                    for e in snapshot.recent
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
