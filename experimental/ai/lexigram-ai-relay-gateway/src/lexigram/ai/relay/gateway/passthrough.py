"""Passthrough relay lifecycle for non-chat endpoint kinds.

``PassthroughService`` relays endpoint kinds that do not fit the
chat-focused conversion engine (starting with embeddings) through the
generalized parts of the chat pipeline — channel selection by endpoint
kind, authorization, billing admission and settlement, and the upstream
HTTP adapter — while skipping ``RelayConverterProtocol`` entirely: the
wire format in is the wire format out, with the model alias
substituted only when the channel config declares a suffix.  Bodies are
carried by :class:`RelayPassthroughBody` (decoded JSON or raw bytes
with a content type) and upstream responses by
:class:`RelayPassthroughResult` (verbatim bytes plus the upstream
content type) — JSON responses are still returned decoded through the
``payload`` accessor so the embeddings wire path is byte-for-byte
unchanged, while non-JSON responses ride in ``body`` uninterpreted.
The upstream response is returned verbatim, unvalidated beyond the
adapter's existing malformed-body handling.

Implementation lives in three focused modules:

- :mod:`lexigram.ai.relay.gateway.passthrough_body` — request body
  carrier and multipart field rewriting.
- :mod:`lexigram.ai.relay.gateway.passthrough_result` — upstream
  response carrier.
- :mod:`lexigram.ai.relay.gateway.passthrough_service` — the
  endpoint-kind dispatch service.

This module re-exports the public surface so existing imports keep
resolving unchanged.
"""

from __future__ import annotations

from lexigram.ai.relay.gateway.passthrough_body import (
    RelayPassthroughBody,
    rewrite_multipart_form_field,
)
from lexigram.ai.relay.gateway.passthrough_result import RelayPassthroughResult
from lexigram.ai.relay.gateway.passthrough_service import PassthroughService

__all__ = [
    "PassthroughService",
    "RelayPassthroughBody",
    "RelayPassthroughResult",
    "rewrite_multipart_form_field",
]
