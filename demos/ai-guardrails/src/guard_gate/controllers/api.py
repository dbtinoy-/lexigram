"""JSON API for the guardrails playground — no HTML lives here."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from guard_gate.repository.acts import ACTS
from guard_gate.services.guarded_assistant import GuardedAssistant
from guard_gate.services.policy import PolicyToggle
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, get, post


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


async def _body(request: Request) -> dict:
    """Parse the request body through the framework serializer."""
    from typing import Any

    raw = await request.body()
    if not raw:
        return {}
    parsed: Any = json_loads(raw)
    return dict(parsed) if isinstance(parsed, dict) else {}


def _serialize(outcome) -> JSONResponse:
    return JSONResponse(
        {
            "outcome": {
                "kind": outcome.kind,
                "reply": outcome.reply,
                "reason": outcome.reason,
                "remaining_budget": outcome.remaining_budget,
            },
        },
    )


class GuardApiController(Controller):
    """Endpoints consumed by ui/static/app.js."""

    def __init__(
        self,
        assistant: GuardedAssistant,
        toggle: PolicyToggle,
    ) -> None:
        self._assistant = assistant
        self._toggle = toggle

    @post("/api/ask")
    async def ask(self, request: Request) -> JSONResponse:
        """Handle an act-keyed or raw-text request."""
        data = await _body(request)
        act_key = str(data.get("act", ""))
        act = ACTS.get(act_key)
        if act_key and act is None:
            return _error(f"unknown act: {act_key!r}", 400)

        text = str(data.get("text", act.text if act else "")).strip()
        model = str(data.get("model", act.model if act else "")).strip()
        user_id = str(data.get("user_id", "demo-user"))

        if not text or not model:
            return _error("text and model are required", 400)

        outcome = await self._assistant.handle(user_id, text, model)
        return _serialize(outcome)

    @post("/api/policy")
    async def policy(self, request: Request) -> JSONResponse:
        """Flip protection on/off."""
        data = await _body(request)
        enabled = bool(data.get("enabled"))
        self._toggle.set(enabled)
        return JSONResponse({"enabled": self._toggle.enabled})

    @get("/api/state")
    async def state(self, request: Request) -> JSONResponse:
        """Toggle position plus budget arithmetic for the meter."""
        return JSONResponse(
            {
                "policy_enabled": self._toggle.enabled,
                "monthly_budget": self._assistant.monthly_budget,
                "spent": round(
                    self._assistant.monthly_budget - self._assistant.remaining, 2
                ),
                "remaining": self._assistant.remaining,
            },
        )

    @get("/api/audit")
    async def audit(self, request: Request) -> JSONResponse:
        """Recent governance audit events."""
        rows = await self._assistant.audit_rows()
        return JSONResponse({"rows": rows})


__all__ = ["GuardApiController"]
