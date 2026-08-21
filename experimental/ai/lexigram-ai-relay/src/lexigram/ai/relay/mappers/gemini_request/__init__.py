"""Google Gemini ``generateContent`` request conversion.

Builds :class:`GeminiRequest` wire payloads from canonical
:class:`RelayRequest` (:func:`ir_to_request`) and parses Gemini request
DTOs back into the relay IR (:func:`request_to_ir`).  Conversion is
split by direction: :mod:`to_ir` parses wire → IR, :mod:`from_ir`
builds wire ← IR, and :mod:`_shared` holds constants plus the
``ToolCall`` to/from Gemini part helpers consumed across directions.
"""

from __future__ import annotations

from lexigram.ai.relay.mappers.gemini_request._shared import (
    _TARGET,
    _tool_call_from_part,
    _tool_call_to_part,
)
from lexigram.ai.relay.mappers.gemini_request.from_ir import ir_to_request
from lexigram.ai.relay.mappers.gemini_request.to_ir import request_to_ir

__all__ = ["ir_to_request", "request_to_ir"]
