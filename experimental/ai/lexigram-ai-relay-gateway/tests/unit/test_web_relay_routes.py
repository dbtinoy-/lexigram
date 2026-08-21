"""Buffered relay endpoint behavior: dispatch, error envelopes, headers, identity."""

from __future__ import annotations

from starlette.responses import JSONResponse

from lexigram.ai.relay.gateway.web.routes import build_routes
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    RelayGatewayResult,
)
from lexigram.contracts.core.result import Err, Ok
from lexigram.serialization import loads

from web_test_helpers import FakeGateway, FakeResolver, FakeRequest, _ok_gateway


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
