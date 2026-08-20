"""Passthrough upstream response carrier.

:class:`RelayPassthroughResult` is the verbatim-bytes response carrier
used by every passthrough wire path: JSON responses additionally expose
their decoded object on ``payload``, while non-JSON responses ride in
``body`` uninterpreted.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass

from lexigram.contracts.ai.relay import (
    JsonValue,
    RelayGatewayMetadata,
    RelayGatewayResult,
    RelayWireEvent,
)

__all__ = ["RelayPassthroughResult"]


@dataclass(frozen=True, slots=True, init=False)
class RelayPassthroughResult(RelayGatewayResult):
    """One passthrough upstream response, decoded when JSON, verbatim otherwise.

    Extends the gateway result carrier with the two fields the passthrough
    wire paths need: the upstream body and its content type.  JSON
    responses keep their decoded object on ``payload`` (byte-for-byte the
    Plan J shape) and additionally populate ``body`` with the serialized
    bytes; non-JSON responses carry the raw bytes in ``body`` with
    ``payload`` left ``None``.  Callers read ``body`` regardless of the
    response shape; the constructor is ``(body, content_type,
    status_code)`` with the inherited gateway fields (headers, payload)
    as optional keywords so existing relay route code keeps compiling.

    Attributes:
        body: The response body bytes (serialized JSON for JSON
            responses, the upstream bytes verbatim otherwise).
        content_type: The upstream ``content-type`` header value.
    """

    body: bytes = b""
    content_type: str = ""

    def __init__(
        self,
        body: bytes = b"",
        content_type: str = "",
        status_code: int = 200,
        *,
        headers: Mapping[str, str] | None = None,
        payload: Mapping[str, JsonValue] | None = None,
        stream: AsyncIterator[RelayWireEvent] | None = None,
        metadata: RelayGatewayMetadata | None = None,
    ) -> None:
        """Bind the passthrough result fields.

        Args:
            body: The response body bytes.
            content_type: The upstream content-type header.
            status_code: The upstream HTTP status code.
            headers: Response headers to relay; defaults to empty.
            payload: Decoded JSON object for JSON responses; ``None``
                for raw bodies.
            stream: Never used by passthrough; always ``None``.
            metadata: Never used by passthrough; always ``None``.
        """
        object.__setattr__(self, "body", body)
        object.__setattr__(self, "content_type", content_type)
        object.__setattr__(self, "status_code", status_code)
        object.__setattr__(self, "headers", headers if headers is not None else {})
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "stream", stream)
        object.__setattr__(self, "metadata", metadata)
