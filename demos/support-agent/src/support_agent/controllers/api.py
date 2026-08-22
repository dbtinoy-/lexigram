"""JSON API for the support-agent console — no HTML lives here.

Handlers return ``Result`` values; the web pipeline renders ``Ok`` payloads
and maps ``Err`` errors to ProblemDetail responses via ``ResultResponseMapper``.
"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request

from lexigram.contracts.ai.agents import AgentError
from lexigram.contracts.exceptions.domain import NotFoundError, ValidationError
from lexigram.result import Err, Result
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, get, post
from lexigram.web.routing.result_bridge import ResultResponseMapper
from support_agent.repository.scenarios import SCENARIOS
from support_agent.repository.scripted_llm import ScriptedLLM
from support_agent.services.support_service import (
    SupportAgent,
    build_support_agent,
)

# Agent failures are infrastructure-level (scripted boundary misuse).
ResultResponseMapper.register(AgentError, 500)


async def _body(request: Request) -> dict[str, Any]:
    """Parse the request body through the framework serializer."""
    raw = await request.body()
    if not raw:
        return {}
    parsed = json_loads(raw)
    return dict(parsed) if isinstance(parsed, dict) else {}


def _payload(response: Any) -> dict[str, Any]:
    return {
        "answer": response.message,
        "steps": [
            {
                "step_number": step.step_number,
                "thought": step.thought,
                "action": step.action,
            }
            for step in response.steps
        ],
        "tool_calls": [
            {
                "tool_name": call.tool_name,
                "succeeded": call.succeeded,
                "error": call.error,
            }
            for call in response.tool_calls
        ],
        "total_tokens": response.total_tokens,
        "duration_ms": round(response.duration_ms, 1),
    }


class AgentApiController(Controller):
    """Endpoints consumed by the ui/static/app.js fetch client."""

    def __init__(self, scripted: ScriptedLLM, support: SupportAgent) -> None:
        self._scripted = scripted
        self._support = support

    @get("/api/tools")
    async def tools(self, request: Request) -> list[dict[str, str]]:
        """List registered tools for the console sidebar."""
        agent = build_support_agent()
        return [{"name": t.name, "description": t.description} for t in agent.tools]

    @post("/api/ask")
    async def ask(
        self,
        request: Request,
    ) -> Result[dict[str, Any], Exception]:
        """Run one scenario-scripted ReAct turn."""
        data = await _body(request)
        scenario_key = str(data.get("scenario", ""))
        scenario = SCENARIOS.get(scenario_key)
        if scenario is None:
            return Err(NotFoundError(f"unknown scenario: {scenario_key!r}"))

        question = str(data.get("question", "")).strip()
        if not question:
            return Err(ValidationError("question is required"))

        self._scripted.load(scenario.script)
        result = await self._support.ask(question)
        return result.map_sync(_payload)


__all__ = ["AgentApiController"]
