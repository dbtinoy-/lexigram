"""Scripted LLM client — deterministic stand-in for ``LLMClientProtocol``.

ReAct drives reasoning through text markers inside completion strings.
This client pops pre-written completions from a FIFO queue so the agent
loop runs for real while model output stays byte-stable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.result import Ok, Result


@dataclass(frozen=True)
class ScriptedUsage:
    """Token accounting reported with each scripted completion."""

    prompt_tokens: int = 12
    completion_tokens: int = 24
    total_tokens: int = 36


@dataclass(frozen=True)
class ScriptedCompletion:
    """Minimal completion carrying the fields strategies consume."""

    content: str
    model: str = "scripted"
    usage: ScriptedUsage = field(default_factory=ScriptedUsage)


class EmptyScriptError(RuntimeError):
    """Raised when the scripted queue drains before the act ends."""


class ScriptedLLM:
    """FIFO queue of pre-written completions implementing the LLM contract."""

    def __init__(self, script: list[str] | None = None) -> None:
        self._script: list[str] = list(script or [])

    @property
    def remaining(self) -> int:
        """Completions left in the queue."""
        return len(self._script)

    def load(self, lines: list[str]) -> None:
        """Replace the queued script (used per scenario)."""
        self._script = list(lines)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[Any] | None = None,
        stop_sequences: list[str] | None = None,
        **kwargs: Any,
    ) -> Result[ScriptedCompletion, Exception]:
        """Pop the next scripted completion."""
        if not self._script:
            raise EmptyScriptError("script exhausted: no completions remain")
        return Ok(ScriptedCompletion(content=self._script.pop(0)))

    async def stream_chat(self, *args: Any, **kwargs: Any) -> Any:
        """Unused by the ReAct strategy."""
        raise NotImplementedError("ScriptedLLM does not support streaming")

    async def health_check(self, timeout: float = 5.0) -> Any:
        """Unused by the demo."""
        raise NotImplementedError

    async def close(self) -> None:
        """Nothing to release."""
        return None
