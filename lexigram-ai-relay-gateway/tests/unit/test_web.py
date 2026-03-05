"""Relay gateway web layer tests (Relay Gateway plan, Task 6).

Covers the raw Starlette route mounting (``RelayGatewayWebContributor``),
the four inbound relay endpoints (``build_routes``), protocol-specific
error envelopes, safe header filtering, SSE framing (``SSEEncoder``), and
request-time gateway resolution.  Endpoints are exercised with a minimal
request double instead of a full ASGI test client.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

from starlette.responses import JSONResponse, StreamingResponse

from lexigram.ai.relay.gateway.web.contributor import RelayGatewayWebContributor
from lexigram.ai.relay.gateway.web.routes import RELAY_ROUTE_PATHS, build_routes
from lexigram.ai.relay.gateway.web.sse import SSEEncoder
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    RelayGatewayProtocol,
    RelayGatewayRequest,
    RelayGatewayResult,
    RelayWireEvent,
)
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.serialization import loads

class FakeGateway(RelayGatewayProtocol):
    """Minimal ``RelayGatewayProtocol`` double recording ``handle`` calls."""

    def __init__(self, outcome: Result[RelayGatewayResult, RelayGatewayError]) -> None:
        self._outcome = outcome
        self.calls: list[RelayGatewayRequest] = []

    async def handle(
        self, request: RelayGatewayRequest
    ) -> Result[RelayGatewayResult, RelayGatewayError]:
        """Record the request and return the canned outcome."""
        self.calls.append(request)
        return self._outcome

class FakeResolver:
    """Async callable returning the configured fake gateway."""

    def __init__(self, gateway: FakeGateway) -> None:
        self._gateway = gateway
        self.calls: list[Any] = []

    async def __call__(self, request: Any) -> RelayGatewayProtocol:
        """Record the request and return the fake gateway."""
        self.calls.append(request)
        return self._gateway

class FakePassthroughService:
    """Minimal ``PassthroughService`` double recording ``handle`` calls."""

    def __init__(
        self,
        outcome: Result[RelayGatewayResult, RelayGatewayError],
    ) -> None:
        self._outcome = outcome
        self.calls: list[tuple[str, RelayGatewayRequest]] = []

    async def handle(
        self, kind: str, request: RelayGatewayRequest
    ) -> Result[RelayGatewayResult, RelayGatewayError]:
        """Record the call and return the canned outcome."""
        self.calls.append((kind, request))
        return self._outcome

class FakePassthroughResolver:
    """Async callable returning the configured fake passthrough service."""

    def __init__(self, service: FakePassthroughService) -> None:
        self._service = service
        self.calls: list[Any] = []

    async def __call__(self, request: Any) -> FakePassthroughService:
        """Record the request and return the fake service."""
        self.calls.append(request)
        return self._service

class FakeRequest:
    """Minimal request double exposing the state/headers surface endpoints use."""

    def __init__(
        self,
        *,
        body: bytes = b"{}",
        request_id: str | None = None,
        user: dict[str, Any] | None = None,
        path_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._body = body
        self.state = SimpleNamespace(request_id=request_id, user=user, container=None)
        self.path_params = path_params if path_params is not None else {}
        self.method = "POST"
        self.headers: dict[str, str] = headers if headers is not None else {}

    async def body(self) -> bytes:
        """Return the canned request body."""
        return self._body

class FakeRoute:
    """Minimal route double carrying the path used by the mount guard."""

    def __init__(self, path: str) -> None:
        self.path = path

class FakeApp:
    """Minimal app double recording ``add_route`` registrations."""

    def __init__(self) -> None:
        self.routes: list[FakeRoute] = []
        self.registrations: list[tuple[str, Any, list[str] | None]] = []

    def add_route(
        self, path: str, endpoint: Any, methods: list[str] | None = None
    ) -> None:
        """Record the registration and make it visible to the mount guard."""
        self.registrations.append((path, endpoint, methods))
        self.routes.append(FakeRoute(path))

def _ok_gateway(headers: dict[str, str] | None = None) -> FakeGateway:
    """Build a gateway returning an empty 200 result."""
    return FakeGateway(
        Ok(
            RelayGatewayResult(
                status_code=200,
                headers=headers if headers is not None else {},
                payload={},
            )
        )
    )

def test_contributor_id() -> None:
    """The contributor exposes its registered identifier."""
    assert RelayGatewayWebContributor().contributor_id == "relay-gateway"

def test_contributor_get_controllers_empty() -> None:
    """Controllers and middleware are contributed by the host, not the gateway."""
    contributor = RelayGatewayWebContributor()
    assert contributor.get_controllers() == []
    assert contributor.get_middleware() == []

async def test_mount_registers_routes_once() -> None:
    """Repeated mounts register each relay path exactly once."""
    app = FakeApp()
    contributor = RelayGatewayWebContributor()
    await contributor.mount_to_app(app, object())
    await contributor.mount_to_app(app, object())
    assert [path for path, _, _ in app.registrations] == list(RELAY_ROUTE_PATHS)
    assert len(app.registrations) == len(RELAY_ROUTE_PATHS)
    for _, _, methods in app.registrations:
        assert methods == ["POST"]

async def test_buffered_openai_chat_success() -> None:
    """A buffered chat result is returned as JSON with request metadata."""
    payload = {"id": "chatcmpl-1", "choices": []}
    gateway = FakeGateway(
        Ok(RelayGatewayResult(status_code=200, headers={}, payload=payload))
    )
    resolver = FakeResolver(gateway)
    endpoint = build_routes(resolver)[0].endpoint
    response = await endpoint(
        FakeRequest(
            body=b'{"model": "gpt-4o", "stream": false}',
            request_id="req-abc",
            user={"id": "u1", "tenant_id": "t1"},
        )
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert loads(response.body) == payload
    assert response.headers.get("x-request-id") == "req-abc"
    assert gateway.calls[0].request_id == "req-abc"
    assert gateway.calls[0].tenant_id == "t1"
    assert gateway.calls[0].model == "gpt-4o"
    assert gateway.calls[0].source is RelayFormat.OPENAI_CHAT
    assert gateway.calls[0].stream is False

async def test_request_id_fallback_uuid() -> None:
    """A missing state request id falls back to a generated uuid."""
    gateway = _ok_gateway()
    resolver = FakeResolver(gateway)
    endpoint = build_routes(resolver)[0].endpoint
    response = await endpoint(FakeRequest(body=b'{"model": "gpt-4o"}'))
    assert response.status_code == 200
    rid = gateway.calls[0].request_id
    assert len(rid) == 36
    assert all(character in "0123456789abcdef-" for character in rid.lower())

async def test_malformed_body_400() -> None:
    """Malformed JSON yields a 400 invalid-request envelope without dispatch."""
    gateway = _ok_gateway()
    resolver = FakeResolver(gateway)
    endpoint = build_routes(resolver)[0].endpoint
    response = await endpoint(FakeRequest(body=b"not json"))
    assert response.status_code == 400
    assert loads(response.body)["error"]["type"] == "invalid_request_error"
    assert gateway.calls == []

async def test_missing_model_400() -> None:
    """A payload without a model yields a 400 before touching the gateway."""
    gateway = _ok_gateway()
    resolver = FakeResolver(gateway)
    endpoint = build_routes(resolver)[0].endpoint
    response = await endpoint(FakeRequest(body=b"{}"))
    assert response.status_code == 400
    assert gateway.calls == []

async def test_gemini_model_from_path() -> None:
    """Gemini takes the model from the path params."""
    gateway = _ok_gateway()
    resolver = FakeResolver(gateway)
    endpoint = build_routes(resolver)[3].endpoint
    request = FakeRequest(
        body=b'{"contents": []}', path_params={"model": "gemini-2.5-pro"}
    )
    response = await endpoint(request)
    assert response.status_code == 200
    assert gateway.calls[0].model == "gemini-2.5-pro"
    assert gateway.calls[0].source is RelayFormat.GEMINI

async def test_error_envelope_matches_inbound() -> None:
    """Gateway errors render in the inbound protocol's envelope per family."""
    error = RelayGatewayError(
        code="UPSTREAM_TIMEOUT",
        message="upstream timed out",
        status_code=504,
        request_id="r1",
    )
    routes = build_routes(FakeResolver(FakeGateway(Err(error))))
    expected = {
        RelayFormat.OPENAI_CHAT: (
            {
                "error": {
                    "message": "upstream timed out",
                    "type": "server_error",
                    "code": "UPSTREAM_TIMEOUT",
                    "request_id": "r1",
                }
            }
        ),
        RelayFormat.OPENAI_RESPONSES: (
            {
                "error": {
                    "message": "upstream timed out",
                    "type": "server_error",
                    "code": "UPSTREAM_TIMEOUT",
                }
            }
        ),
        RelayFormat.CLAUDE: (
            {
                "type": "error",
                "error": {"type": "api_error", "message": "upstream timed out"},
            }
        ),
        RelayFormat.GEMINI: (
            {
                "error": {
                    "code": 504,
                    "message": "upstream timed out",
                    "status": "DEADLINE_EXCEEDED",
                }
            }
        ),
    }
    for index, source in enumerate(
        [
            RelayFormat.OPENAI_CHAT,
            RelayFormat.OPENAI_RESPONSES,
            RelayFormat.CLAUDE,
            RelayFormat.GEMINI,
        ]
    ):
        response = await routes[index].endpoint(FakeRequest(body=b'{"model": "m"}'))
        assert response.status_code == 504
        assert loads(response.body) == expected[source]

async def test_error_status_mapping_429() -> None:
    """Status codes map to protocol error types (403 and 429)."""
    routes = build_routes(
        FakeResolver(
            FakeGateway(
                Err(
                    RelayGatewayError(
                        code="AUTH_DENIED",
                        message="denied",
                        status_code=403,
                        request_id="r1",
                    )
                )
            )
        )
    )
    response = await routes[0].endpoint(FakeRequest(body=b'{"model": "m"}'))
    assert response.status_code == 403
    assert loads(response.body)["error"]["type"] == "permission_denied_error"

    routes = build_routes(
        FakeResolver(
            FakeGateway(
                Err(
                    RelayGatewayError(
                        code="UPSTREAM_ERROR",
                        message="rate limited",
                        status_code=429,
                        request_id="r2",
                    )
                )
            )
        )
    )
    response = await routes[0].endpoint(FakeRequest(body=b'{"model": "m"}'))
    assert response.status_code == 429
    assert loads(response.body)["error"]["type"] == "rate_limit_error"

async def test_buffered_headers_filtered() -> None:
    """Hop-by-hop and set-cookie headers are dropped; safe ones survive."""
    gateway = FakeGateway(
        Ok(
            RelayGatewayResult(
                status_code=200,
                headers={
                    "set-cookie": "a=b",
                    "connection": "keep-alive",
                    "x-custom": "1",
                },
                payload={"ok": True},
            )
        )
    )
    resolver = FakeResolver(gateway)
    endpoint = build_routes(resolver)[0].endpoint
    response = await endpoint(
        FakeRequest(body=b'{"model": "gpt-4o"}', request_id="req-9")
    )
    assert response.headers.get("x-custom") == "1"
    assert "set-cookie" not in {key.lower() for key in response.headers.keys()}
    assert "connection" not in {key.lower() for key in response.headers.keys()}
    assert response.headers.get("x-request-id") == "req-9"

async def _terminal_stream() -> AsyncIterator[RelayWireEvent]:
    """One terminal wire event."""
    yield RelayWireEvent(event=None, data=None, terminal=True)

async def test_streaming_response_headers() -> None:
    """Streaming results produce SSE responses with stream headers."""
    gateway = FakeGateway(
        Ok(RelayGatewayResult(status_code=200, headers={}, stream=_terminal_stream()))
    )
    resolver = FakeResolver(gateway)
    endpoint = build_routes(resolver)[0].endpoint
    response = await endpoint(
        FakeRequest(body=b'{"model": "gpt-4o", "stream": true}', request_id="req-s")
    )
    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/event-stream"
    assert response.headers.get("cache-control") == "no-cache"
    assert response.headers.get("connection") == "keep-alive"
    assert response.headers.get("x-request-id") == "req-s"

def test_sse_openai_chat_framing() -> None:
    """OpenAI Chat frames data-only chunks and terminates with ``[DONE]``."""
    encoder = SSEEncoder(RelayFormat.OPENAI_CHAT)
    assert encoder.encode(RelayWireEvent(None, {"choices": []}, False)) == (
        b'data: {"choices":[]}\n\n'
    )
    assert encoder.encode(RelayWireEvent(None, None, True)) == b"data: [DONE]\n\n"
    assert encoder.encode(RelayWireEvent(None, {"choices": []}, True)) == (
        b'data: {"choices":[]}\n\ndata: [DONE]\n\n'
    )
    assert encoder.encode_terminal(RelayFormat.OPENAI_CHAT, None) == (
        b"data: [DONE]\n\n"
    )
    assert (
        encoder.encode_terminal(
            RelayFormat.OPENAI_CHAT, RelayWireEvent(None, None, True)
        )
        == b""
    )

def test_sse_responses_event_framing() -> None:
    """OpenAI Responses frames carry the event name above the data line."""
    encoder = SSEEncoder(RelayFormat.OPENAI_RESPONSES)
    frame = encoder.encode(
        RelayWireEvent(
            "response.output_text.delta",
            {"type": "response.output_text.delta", "delta": "hi"},
            False,
        )
    )
    assert frame.startswith(b"event: response.output_text.delta\n")
    assert b"data: " in frame

def test_sse_claude_framing() -> None:
    """Claude frames carry the event name above the data line."""
    encoder = SSEEncoder(RelayFormat.CLAUDE)
    frame = encoder.encode(
        RelayWireEvent(
            "content_block_delta",
            {"type": "content_block_delta", "delta": "x"},
            False,
        )
    )
    assert frame.startswith(b"event: content_block_delta\n")
    assert b"data: " in frame

def test_sse_gemini_framing() -> None:
    """Gemini frames data-only lines with no event name or terminator."""
    encoder = SSEEncoder(RelayFormat.GEMINI)
    frame = encoder.encode(RelayWireEvent(None, {"candidates": []}, False))
    assert frame == b'data: {"candidates":[]}\n\n'
    assert b"event:" not in frame

async def _chat_stream() -> AsyncIterator[RelayWireEvent]:
    """One delta chunk followed by the terminal event."""
    yield RelayWireEvent(None, {"choices": [{"delta": {"content": "hi"}}]}, False)
    yield RelayWireEvent(None, None, True)

async def test_stream_events_pass_through() -> None:
    """Every wire event becomes a frame; terminal emits exactly one ``[DONE]``."""
    gateway = FakeGateway(
        Ok(RelayGatewayResult(status_code=200, headers={}, stream=_chat_stream()))
    )
    resolver = FakeResolver(gateway)
    endpoint = build_routes(resolver)[0].endpoint
    response = await endpoint(FakeRequest(body=b'{"model": "gpt-4o", "stream": true}'))
    frames = [frame async for frame in response.body_iterator]
    assert frames[0].startswith(b"data: ")
    assert frames[-1] == b"data: [DONE]\n\n"
    assert frames.count(b"data: [DONE]\n\n") == 1

async def test_identity_from_state_user() -> None:
    """Tenant id is read from the normalized auth user dict."""
    gateway = _ok_gateway()
    resolver = FakeResolver(gateway)
    endpoint = build_routes(resolver)[0].endpoint
    await endpoint(
        FakeRequest(body=b'{"model": "gpt-4o"}', user={"id": "u1", "tenant_id": "t1"})
    )
    assert gateway.calls[0].tenant_id == "t1"
    await endpoint(FakeRequest(body=b'{"model": "gpt-4o"}', user=None))
    assert gateway.calls[1].tenant_id == ""

class TestEmbeddingsRoute:
    """``POST /v1/embeddings`` passthrough route behavior."""

    @staticmethod
    def embeddings_endpoint(
        service: FakePassthrough,
    ) -> Any:
        routes = build_routes(
            FakeResolver(FakeGateway(_ok_gateway()._outcome)),
            resolve_passthrough=FakePassthroughResolver(service),
        )
        return routes[-1]

    async def test_buffered_embeddings_success(self) -> None:
        payload = {"object": "list", "data": [{"embedding": [0.1]}]}
        service = FakePassthroughService(
            Ok(RelayGatewayResult(status_code=200, headers={}, payload=payload))
        )
        endpoint = self.embeddings_endpoint(service).endpoint
        response = await endpoint(
            FakeRequest(
                body=b'{"model": "text-embedding-3-small", "input": "hi"}',
                request_id="req-emb",
                user={"id": "u1", "tenant_id": "t1"},
            )
        )
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert loads(response.body) == payload
        assert response.headers.get("x-request-id") == "req-emb"
        kind, request = service.calls[0]
        assert kind == "embeddings"
        assert request.request_id == "req-emb"
        assert request.tenant_id == "t1"
        assert request.model == "text-embedding-3-small"
        assert request.source is RelayFormat.OPENAI_CHAT
        assert request.stream is False
        assert request.channel is None
        assert request.payload == {"model": "text-embedding-3-small", "input": "hi"}

    async def test_embeddings_error_uses_openai_envelope(self) -> None:
        service = FakePassthroughService(
            Err(
                RelayGatewayError(
                    code="MODEL_NOT_FOUND",
                    message="no channel serves endpoint 'embeddings'",
                    status_code=404,
                    request_id="req-emb",
                )
            )
        )
        endpoint = self.embeddings_endpoint(service).endpoint
        response = await endpoint(
            FakeRequest(
                body=b'{"model": "unknown-model", "input": "hi"}',
                request_id="req-emb",
            )
        )
        assert response.status_code == 404
        assert loads(response.body) == {
            "error": {
                "message": "no channel serves endpoint 'embeddings'",
                "type": "invalid_request_error",
                "code": "MODEL_NOT_FOUND",
                "request_id": "req-emb",
            }
        }

    async def test_embeddings_missing_model_400(self) -> None:
        service = FakePassthroughService(
            Ok(RelayGatewayResult(status_code=200, headers={}, payload={}))
        )
        endpoint = self.embeddings_endpoint(service).endpoint
        response = await endpoint(FakeRequest(body=b"{}"))
        assert response.status_code == 400
        assert response.headers.get("x-request-id") is None
        assert service.calls == []

    async def test_embeddings_malformed_body_400(self) -> None:
        service = FakePassthroughService(
            Ok(RelayGatewayResult(status_code=200, headers={}, payload={}))
        )
        endpoint = self.embeddings_endpoint(service).endpoint
        response = await endpoint(FakeRequest(body=b"not json"))
        assert response.status_code == 400
        assert service.calls == []

    async def test_embeddings_route_registered_in_mount(self) -> None:
        service = FakePassthroughService(
            Ok(RelayGatewayResult(status_code=200, headers={}, payload={}))
        )
        routes = build_routes(
            FakeResolver(_ok_gateway()),
            resolve_passthrough=FakePassthroughResolver(service),
        )
        paths = [route.path for route in routes]
        assert "/v1/embeddings" in paths
        assert paths[-1] == "/v1/embeddings"
        assert RELAY_ROUTE_PATHS[-1] == "/v1/embeddings"

