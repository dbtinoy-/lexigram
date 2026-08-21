"""Shared builders for the Gemini mapper test suite.

Imported by the per-direction Gemini mapper test modules; not a test
module itself.  The module-level ``mapper`` constant deliberately
shadows nothing: the directory conftest's ``mapper`` fixture returns
the OpenAI Responses mapper, so Gemini tests use this constant instead.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.mappers.gemini import GeminiMapper
from lexigram.contracts.ai.relay.dto import GeminiContent, GeminiPart, GeminiRequest
from lexigram.contracts.core.result import Ok

mapper = GeminiMapper()


def gemini_req(**kwargs: Any) -> GeminiRequest:
    """Build a Gemini request with sensible defaults."""
    defaults: dict[str, Any] = {"contents": []}
    defaults.update(kwargs)
    return GeminiRequest(**defaults)


def gemini_content(role: str, *parts: GeminiPart) -> GeminiContent:
    """Build a Gemini content turn."""
    return GeminiContent(role=role, parts=list(parts))


def gen_config(**kwargs: Any) -> dict[str, Any]:
    """Build a generationConfig dict."""
    return {k: v for k, v in kwargs.items() if v is not None}


def text_part(text: str) -> GeminiPart:
    """Build a text part."""
    return GeminiPart(text=text)


def thought_part(text: str, signature: str | None = None) -> GeminiPart:
    """Build a thought part."""
    return GeminiPart(text=text, thought=True, thought_signature=signature)


def inline_part(mime_type: str, data: str) -> GeminiPart:
    """Build an inlineData image part."""
    return GeminiPart(inline_data={"mimeType": mime_type, "data": data})


def function_call_part(name: str, args: dict[str, Any]) -> GeminiPart:
    """Build a functionCall part."""
    return GeminiPart(function_call={"name": name, "args": args})


def function_response_part(name: str, response: Any) -> GeminiPart:
    """Build a functionResponse part."""
    return GeminiPart(function_response={"name": name, "response": response})


class FakeResolver:
    """Structural media resolver returning a fixed base64 payload."""

    def resolve(self, url: str) -> object:
        return Ok(("image/png", "AAAB"))
