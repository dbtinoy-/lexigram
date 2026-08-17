"""Wire JSON decode/encode with protocol-specific DTO construction.

The relay gateway speaks four wire formats (OpenAI Chat, OpenAI
Responses, Claude, Gemini). This module owns the boundary between raw
wire JSON bytes and the typed request DTOs from ``lexigram-contracts``:
decode validates the JSON object root and required fields, and encode
serializes a converted DTO back to bytes while preserving the DTOs'
None-omission semantics.
"""

from __future__ import annotations

from typing import Any, TypeAlias

from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay import (
    ClaudeRequest,
    GeminiRequest,
    OpenAIChatRequest,
    RelayFormat,
    RelayGatewayError,
    RelayResponsePayload,
    ResponsesRequest,
)
from lexigram.contracts.ai.relay.dto import (
    ClaudeResponse,
    GeminiResponse,
    OpenAIChatResponse,
    ResponsesResponse,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.serialization import dumps, loads

__all__ = ["RelayPayloadCodec"]

WireRequest: TypeAlias = (
    OpenAIChatRequest | ResponsesRequest | ClaudeRequest | GeminiRequest
)
"""Any typed request DTO accepted by the relay gateway."""

_REQUEST_TYPES: dict[RelayFormat, type[WireRequest]] = {
    RelayFormat.OPENAI_CHAT: OpenAIChatRequest,
    RelayFormat.OPENAI_RESPONSES: ResponsesRequest,
    RelayFormat.CLAUDE: ClaudeRequest,
    RelayFormat.GEMINI: GeminiRequest,
}
"""Map each wire format to its request DTO class."""

_RESPONSE_TYPES: dict[RelayFormat, type[RelayResponsePayload]] = {
    RelayFormat.OPENAI_CHAT: OpenAIChatResponse,
    RelayFormat.OPENAI_RESPONSES: ResponsesResponse,
    RelayFormat.CLAUDE: ClaudeResponse,
    RelayFormat.GEMINI: GeminiResponse,
}
"""Map each wire format to its response DTO class."""


class RelayPayloadCodec:
    """Decode and encode relay wire payloads as typed DTOs.

    The codec is stateless; a single instance can be shared. Decoding
    rejects malformed JSON, non-object roots, and DTOs missing required
    fields; unknown wire fields are preserved verbatim in the DTO
    ``passthrough`` dict and re-emitted on encode.
    """

    def decode_request(
        self,
        source: RelayFormat,
        raw: bytes,
        request_id: str,
    ) -> Result[WireRequest, RelayGatewayError]:
        """Decode wire JSON bytes into the request DTO for *source*.

        Args:
            source: Wire format the payload claims to be.
            raw: Raw request body bytes.
            request_id: Caller-supplied request id stamped on errors.

        Returns:
            ``Ok(dto)`` with unknown fields preserved in the DTO's
            ``passthrough``, or ``Err(RelayGatewayError)`` classifying
            malformed JSON (``INVALID_REQUEST``), non-object roots
            (``INVALID_REQUEST``), unknown formats
            (``UNSUPPORTED_FORMAT``), and missing required fields
            (``INVALID_REQUEST`` carrying the field path).
        """
        try:
            decoded = loads(raw)
        except ValueError:
            return Err(
                RelayGatewayError(
                    code="INVALID_REQUEST",
                    message="malformed JSON",
                    status_code=400,
                    request_id=request_id,
                )
            )
        if not isinstance(decoded, dict):
            return Err(
                RelayGatewayError(
                    code="INVALID_REQUEST",
                    message="payload must be a JSON object",
                    status_code=400,
                    request_id=request_id,
                )
            )
        dto_type = _REQUEST_TYPES.get(source)
        if dto_type is None:
            return Err(
                RelayGatewayError(
                    code="UNSUPPORTED_FORMAT",
                    message=f"unsupported relay format: {source}",
                    status_code=400,
                    request_id=request_id,
                )
            )
        try:
            dto = dto_type.from_dict(decoded)
        except RelayError as relay_error:
            return Err(
                RelayGatewayError(
                    code="INVALID_REQUEST",
                    message=str(relay_error),
                    status_code=400,
                    request_id=request_id,
                )
            )
        return Ok(dto)

    def decode_response_payload(
        self,
        target: RelayFormat,
        data: dict[str, Any],
        request_id: str,
    ) -> Result[RelayResponsePayload, RelayGatewayError]:
        """Decode an upstream wire dict into the response DTO for *target*.

        Args:
            target: Wire format the upstream claims to speak.
            data: Decoded upstream response body.
            request_id: Caller-supplied request id stamped on errors.

        Returns:
            ``Ok(dto)`` with unknown fields preserved in the DTO's
            ``passthrough``, or ``Err(RelayGatewayError)`` classifying
            unknown formats (``UNSUPPORTED_FORMAT``) and DTOs missing
            required fields (``UPSTREAM_MALFORMED`` — a malformed
            upstream response is a 502, not a client 400).
        """
        dto_type = _RESPONSE_TYPES.get(target)
        if dto_type is None:
            return Err(
                RelayGatewayError(
                    code=RelayGatewayErrorCode.UNSUPPORTED_FORMAT,
                    message=f"unsupported relay format: {target}",
                    status_code=400,
                    request_id=request_id,
                )
            )
        try:
            dto = dto_type.from_dict(data)
        except RelayError as relay_error:
            return Err(
                RelayGatewayError(
                    code=RelayGatewayErrorCode.UPSTREAM_MALFORMED,
                    message=relay_error.message,
                    status_code=502,
                    request_id=request_id,
                    retryable=False,
                )
            )
        return Ok(dto)

    def encode(self, dto: WireRequest) -> Result[bytes, RelayGatewayError]:
        """Serialize a request DTO to wire JSON bytes.

        Args:
            dto: Typed request DTO to serialize.

        Returns:
            ``Ok(bytes)`` with ``None`` fields omitted and falsey values
            preserved, or ``Err(RelayGatewayError)`` with code
            ``ENCODE_FAILED`` when the payload cannot be serialized.
        """
        try:
            return Ok(dumps(dto.to_dict()))
        except (TypeError, ValueError):
            return Err(
                RelayGatewayError(
                    code="ENCODE_FAILED",
                    message="failed to serialize payload",
                    status_code=500,
                    request_id="",
                )
            )
