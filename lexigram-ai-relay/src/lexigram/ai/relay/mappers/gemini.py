"""Google Gemini ``generateContent`` request and response mapper.

Converts the Gemini wire DTOs (:class:`GeminiRequest` /
:class:`GeminiResponse`) into the canonical relay IR and back.  Stream
conversion is handled by the shared stream lifecycle task and reports
``unsupported_feature`` until then.

Request conversion lives in :mod:`gemini_request`; response conversion
in :mod:`gemini_response`; this module wires both into
:class:`GeminiMapper`.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import unsupported_feature
from lexigram.ai.relay.mappers.gemini_request import (
    _TARGET,
)
from lexigram.ai.relay.mappers.gemini_request import (
    ir_to_request as _ir_to_request,
)
from lexigram.ai.relay.mappers.gemini_request import (
    request_to_ir as _request_to_ir,
)
from lexigram.ai.relay.mappers.gemini_response import (
    ir_to_response as _ir_to_response,
)
from lexigram.ai.relay.mappers.gemini_response import (
    response_to_ir as _response_to_ir,
)
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.ir import (
    RelayRequest,
    RelayResponse,
    StreamDelta,
    StreamState,
)
from lexigram.contracts.core.result import Err, Result

__all__ = ["GeminiMapper"]


class GeminiMapper:
    """Bidirectional Google Gemini ``generateContent`` converter.

    Attributes:
        format: The wire format this mapper handles.
    """

    format = _TARGET

    def request_to_ir(
        self, payload: Any, *, context: ConversionContext
    ) -> Result[RelayRequest, RelayError]:
        """Convert a ``GeminiRequest`` into canonical ``RelayRequest``.

        Args:
            payload: A wire request DTO.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(request) on success, Err(relay_error) on malformed payload.
        """
        return _request_to_ir(payload, context=context)

    def ir_to_request(
        self, request: RelayRequest, *, context: ConversionContext
    ) -> Result[Any, RelayError]:
        """Convert canonical ``RelayRequest`` into a ``GeminiRequest``.

        Args:
            request: Canonical request IR.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(request) on success, Err(relay_error) on failure.
        """
        return _ir_to_request(request, context=context)

    def response_to_ir(
        self, payload: Any, *, context: ConversionContext
    ) -> Result[RelayResponse, RelayError]:
        """Convert a ``GeminiResponse`` into canonical ``RelayResponse``.

        Args:
            payload: A wire response DTO.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(response) on success, Err(relay_error) on malformed payload.
        """
        return _response_to_ir(payload, context=context)

    def ir_to_response(
        self, response: RelayResponse, *, context: ConversionContext
    ) -> Result[Any, RelayError]:
        """Convert canonical ``RelayResponse`` into a ``GeminiResponse``.

        Args:
            response: Canonical response IR.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(response) on success, Err(relay_error) on failure.
        """
        return _ir_to_response(response, context=context)

    def stream_to_delta(
        self, event: Any, *, state: StreamState
    ) -> Result[tuple[StreamDelta, ...], RelayError]:
        """Stream conversion is deferred to the shared stream lifecycle task."""
        return Err(
            unsupported_feature("gemini stream conversion is not implemented yet")
        )

    def delta_to_stream(
        self, delta: StreamDelta, *, state: StreamState
    ) -> Result[tuple[Any, ...], RelayError]:
        """Stream conversion is deferred to the shared stream lifecycle task."""
        return Err(
            unsupported_feature("gemini stream conversion is not implemented yet")
        )
