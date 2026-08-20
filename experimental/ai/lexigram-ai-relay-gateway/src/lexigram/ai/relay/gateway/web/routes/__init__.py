from __future__ import annotations

"""Inbound relay HTTP routes for the gateway web layer.

Each route owns one inbound wire format (OpenAI Chat, OpenAI Responses,
Claude, Gemini) and serves it through a shared endpoint.  The gateway
implementation is resolved at request time from the request-scoped DI
container.  Buffered results return JSON; streaming results return SSE
frames in the client's own protocol; failures render in the inbound
protocol's error envelope with safe, filtered headers.

Passthrough routes (``POST /v1/embeddings``, ``/v1/rerank``,
``/v1/moderations``, the ``/v1/audio/*`` and ``/v1/images/*`` routes)
serve non-chat endpoint kinds through ``PassthroughService``.  Job-relay
routes (``POST /v1/videos`` and ``GET /v1/videos/{job_id}``) serve
submit-then-poll endpoint kinds through ``JobPassthroughService``.

Endpoint implementations live in sibling modules grouped by concern
(``relay``, ``passthrough``, ``jobs``, ``models``, ``health``,
``builder``); shared machinery and route tables live in ``common`` and
``tables``.
"""

from lexigram.ai.relay.gateway.web.routes.builder import build_routes
from lexigram.ai.relay.gateway.web.routes.common import (
    _resolve_verifier,
    _with_auth_guard,
)
from lexigram.ai.relay.gateway.web.routes.health import health_endpoint
from lexigram.ai.relay.gateway.web.routes.relay import relay_endpoint
from lexigram.ai.relay.gateway.web.routes.tables import (
    MODEL_ROUTE_PATHS,
    RELAY_ROUTE_PATHS,
)

__all__ = [
    "MODEL_ROUTE_PATHS",
    "RELAY_ROUTE_PATHS",
    "build_routes",
    "health_endpoint",
    "relay_endpoint",
]
