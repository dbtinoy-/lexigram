"""JSON API for the support-agent console — no HTML lives here."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.web import Controller, get, post
from support_agent.agent_service import SupportAgent, build_support_agent
from support_agent.llm import ScriptedLLM
from support_agent.scripts import SCENARIOS


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def _serialize(response: Any) -> JSONResponse:
    return JSONResponse(
        {
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
        },
    )


class AgentApiController(Controller):
    """Endpoints consumed by the ui/static/app.js fetch client."""

    def __init__(self, scripted: ScriptedLLM, support: SupportAgent) -> None:
        self._scripted = scripted
        self._support = support

    @get("/api/tools")
    async def tools(self, request: Request) -> JSONResponse:
        """List registered tools for the console sidebar."""
        agent = build_support_agent()
        return JSONResponse(
            [{"name": t.name, "description": t.description} for t in agent.tools],
        )

    @post("/api/ask")
    async def ask(self, request: Request) -> JSONResponse:
        """Run one scenario-scripted ReAct turn."""
        data = await request.json()
        scenario = SCENARIOS.get(str(data.get("scenario", "")))
        if scenario is None:
            return _error(f"unknown scenario: {data.get('scenario')!r}", 400)

        question = str(data.get("question", "")).strip()
        if not question:
            return _error("question is required", 400)

        self._scripted.load(scenario.script)
        result = await self._support.ask(question)
        if result.is_err():
            return _error(str(result.unwrap_err()), 500)
        return _serialize(result.unwrap())


__all__ = ["AgentApiController"]
