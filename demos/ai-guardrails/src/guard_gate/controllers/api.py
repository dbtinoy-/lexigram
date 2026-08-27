"""JSON API for the guardrails playground — no HTML lives here.

Handlers return ``Result`` values; the web pipeline renders ``Ok`` payloads
and maps ``Err`` errors to ProblemDetail responses automatically.

Controllers are the HTTP surface in Lexigram.  They:
- Accept Request objects (Starlette)
- Return Result[dict, DomainError] for automatic error mapping
- Are registered in app.py via WebModule.configure(controllers=[...])
- Get their dependencies injected by the container (see __init__)

For a real app, add more controllers (e.g. AuthController, AdminController)
and register them in app.py.
"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request

from guard_gate.domain.guarded_assistant import GuardedAssistant
from guard_gate.domain.policy import PolicyToggle
from guard_gate.repository.acts import ACTS
from lexigram.contracts.exceptions import NotFoundError, ValidationError
from lexigram.result import Err, Ok, Result
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, JSONResponse, get, post


async def _body(request: Request) -> dict[str, Any]:
    """Parse the request body through the framework serializer."""
    raw = await request.body()
    if not raw:
        return {}
    parsed: Any = json_loads(raw)
    return dict(parsed) if isinstance(parsed, dict) else {}


def _serialize(outcome: Any) -> JSONResponse:
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
    """Endpoints consumed by ui/static/app.js.

    The Controller base class from lexigram.web provides
    route decorators (@get, @post, etc.) and integrates with the
    DI container.  Dependencies (assistant, toggle) are injected —
    the controller never instantiates them directly.
    """

    def __init__(
        self,
        assistant: GuardedAssistant,
        toggle: PolicyToggle,
    ) -> None:
        self._assistant = assistant
        self._toggle = toggle

    @post("/api/ask")
    async def ask(
        self,
        request: Request,
    ) -> Result[dict, NotFoundError | ValidationError]:
        """Handle an act-keyed or raw-text request.

        Return type is Result[dict, DomainError].  The web
        framework automatically serializes Ok(dict) as 200 JSON and
        maps Err(DomainError) to ProblemDetail (RFC 9457) responses.
        You never write try/except for HTTP error handling.
        """
        data = await _body(request)
        act_key = str(data.get("act", ""))
        act = ACTS.get(act_key) if act_key in ACTS else None
        if act_key and act is None:
            return Err(NotFoundError(f"unknown act: {act_key!r}"))

        text = str(data.get("text", act.text if act else "")).strip()
        model = str(data.get("model", act.model if act else "")).strip()
        user_id = str(data.get("user_id", "demo-user"))

        if not text or not model:
            return Err(ValidationError("text and model are required"))

        outcome = await self._assistant.handle(user_id, text, model)
        return Ok(
            {
                "outcome": {
                    "kind": outcome.kind,
                    "reply": outcome.reply,
                    "reason": outcome.reason,
                    "remaining_budget": outcome.remaining_budget,
                },
            },
        )

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
