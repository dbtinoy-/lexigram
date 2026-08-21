"""Tests for the Gemini ``generateContent`` mapper protocol surface.

Direction-specific suites live in sibling modules:

- ``test_gemini_mapper_request_to_ir`` — wire request to canonical IR.
- ``test_gemini_mapper_ir_to_request`` — canonical IR to wire request.
- ``test_gemini_mapper_response_to_ir`` — wire response to canonical IR.
- ``test_gemini_mapper_ir_to_response`` — canonical IR to wire response.
"""

from __future__ import annotations

from gemini_mapper_test_helpers import mapper
from lexigram.ai.relay.mappers.base import FormatMapper
from lexigram.contracts.ai.relay.types import RelayFormat


def test_mapper_implements_format_mapper_protocol() -> None:
    """The Gemini mapper satisfies the FormatMapper protocol."""
    assert isinstance(mapper, FormatMapper)
    assert mapper.format is RelayFormat.GEMINI
