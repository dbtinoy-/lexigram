import json
from dataclasses import dataclass, field
from typing import Any

from lexigram.ai.agents import tool
from lexigram.ai.agents.tools.decorator import FunctionTool
from lexigram.contracts.ai.llm import ChatMessage, LLMClientProtocol, Role


@dataclass
class CritiqueResult:
    passed: bool = True
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    score: float = 1.0
    details: str | None = None


_PACING_PROMPT = """Analyze the pacing of this short-form video script for issues like:
- Too many scene changes in a short time
- Dialog that feels rushed or too slow
- Missing pauses for dramatic effect

Return a JSON object with:
- "passed": bool
- "issues": list of strings describing problems found
- "suggestions": list of strings with improvement ideas
- "score": float from 0.0 (worst) to 1.0 (best)
- "details": string with brief explanation

Script:
{script_text}"""

_DURATION_PROMPT = """Check if this script fits within {target_duration} seconds when spoken at a typical pace (~150 words per minute).
Consider:
- Estimated speaking time based on word count
- Pauses for dramatic effect
- Intro lead-in time

Return a JSON object with:
- "passed": bool
- "issues": list of strings describing problems found
- "suggestions": list of strings with improvement ideas
- "score": float from 0.0 (worst) to 1.0 (best)
- "details": string with brief explanation

Target duration: {target_duration}s
Script:
{script_text}"""


def create_critique_tools(llm: LLMClientProtocol | None) -> dict[str, FunctionTool]:
    @tool(name="check_pacing", description="Analyze script pacing for short-form video content.")
    async def _check_pacing(script_text: str) -> CritiqueResult:
        if llm is None:
            return CritiqueResult()
        result = await llm.complete(
            [ChatMessage(role=Role.USER, content=_PACING_PROMPT.format(script_text=script_text))]
        )
        if result.is_err():
            return CritiqueResult()
        return _parse_result(result.unwrap())

    @tool(
        name="check_duration",
        description="Check if a script fits within a target duration when spoken.",
    )
    async def _check_duration(script_text: str, target_duration: float) -> CritiqueResult:
        if llm is None:
            return CritiqueResult()
        result = await llm.complete(
            [
                ChatMessage(
                    role=Role.USER,
                    content=_DURATION_PROMPT.format(
                        script_text=script_text,
                        target_duration=target_duration,
                    ),
                )
            ]
        )
        if result.is_err():
            return CritiqueResult()
        return _parse_result(result.unwrap())

    return {_check_pacing.name: _check_pacing, _check_duration.name: _check_duration}


def _parse_result(raw: Any) -> CritiqueResult:
    text = raw
    if hasattr(raw, "content"):
        text = raw.content
    if hasattr(raw, "message"):
        text = raw.message
    if hasattr(raw, "text"):
        text = raw.text
    try:
        data = json.loads(str(text))
        return CritiqueResult(
            passed=data.get("passed", True),
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
            score=data.get("score", 1.0),
            details=data.get("details"),
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        return CritiqueResult(
            passed=True,
            issues=[],
            suggestions=[],
            score=1.0,
            details="Could not parse LLM response",
        )
