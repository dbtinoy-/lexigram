"""ScriptedLLMClient — deterministic test stand-in for real LLM clients.

Provides pre-scripted responses for testing without making real API calls.
This is the recommended pattern for testing LLM-dependent services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScriptedLLMClient:
    """A fake LLM client that returns pre-scripted responses.

    Usage::

        client = ScriptedLLMClient(
            responses={
                "generate": "This is a professional product description.",
                "extract": '{"name": "Widget", "price": 29.99}',
            }
        )
        result = await client.complete("generate", "Write a description")
        assert result == "This is a professional product description."
    """

    responses: dict[str, str] = field(default_factory=dict)
    call_log: list[dict[str, Any]] = field(default_factory=list)

    async def complete(self, prompt: str, **kwargs: Any) -> str:
        """Return a scripted response based on the prompt.

        Matches the prompt against stored response keys. If no match,
        returns a default response.
        """
        self.call_log.append({"prompt": prompt, "kwargs": kwargs})

        for key, response in self.responses.items():
            if key.lower() in prompt.lower():
                return response

        return "No scripted response for this prompt."

    async def stream(self, prompt: str, **kwargs: Any) -> list[str]:
        """Return a scripted response as a list of chunks."""
        response = await self.complete(prompt, **kwargs)
        words = response.split()
        return [f"{word} " for word in words]

    def reset(self) -> None:
        """Clear the call log."""
        self.call_log.clear()
