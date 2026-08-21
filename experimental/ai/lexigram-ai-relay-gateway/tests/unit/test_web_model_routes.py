"""Model passthrough routes: embeddings, rerank, moderations."""

from __future__ import annotations

from typing import Any

from starlette.responses import JSONResponse

from lexigram.ai.relay.gateway.web.routes import RELAY_ROUTE_PATHS, build_routes
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    RelayGatewayResult,
)
from lexigram.contracts.core.result import Err, Ok
from lexigram.serialization import loads

from web_test_helpers import (
    FakeGateway,
    FakePassthroughResolver,
    FakePassthroughService,
    FakeRequest,
    FakeResolver,
    _ok_gateway,
)


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
        return next(r for r in routes if r.path == "/v1/embeddings")

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
        assert paths[-1] == "/v1/images/edits"
        assert RELAY_ROUTE_PATHS[-1] == "/v1/images/edits"

class TestRerankRoute:
    """``POST /v1/rerank`` passthrough route behavior."""

    @staticmethod
    def rerank_endpoint(service: FakePassthrough) -> Any:
        routes = build_routes(
            FakeResolver(FakeGateway(_ok_gateway()._outcome)),
            resolve_passthrough=FakePassthroughResolver(service),
        )
        return next(r for r in routes if r.path == "/v1/rerank")

    async def test_buffered_rerank_success(self) -> None:
        payload = {"object": "list", "data": [{"index": 0, "relevance_score": 0.9}]}
        service = FakePassthroughService(
            Ok(RelayGatewayResult(status_code=200, headers={}, payload=payload))
        )
        endpoint = self.rerank_endpoint(service).endpoint
        response = await endpoint(
            FakeRequest(
                body=b'{"model": "ranker-1", "query": "q", "documents": ["d"]}',
                request_id="req-rerank",
                user={"id": "u1", "tenant_id": "t1"},
            )
        )
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert loads(response.body) == payload
        assert response.headers.get("x-request-id") == "req-rerank"
        kind, request = service.calls[0]
        assert kind == "rerank"
        assert request.request_id == "req-rerank"
        assert request.tenant_id == "t1"
        assert request.model == "ranker-1"
        assert request.source is RelayFormat.OPENAI_CHAT
        assert request.stream is False
        assert request.channel is None
        assert request.payload == {"model": "ranker-1", "query": "q", "documents": ["d"]}

    async def test_rerank_error_uses_openai_envelope(self) -> None:
        service = FakePassthroughService(
            Err(
                RelayGatewayError(
                    code="MODEL_NOT_FOUND",
                    message="no channel serves endpoint 'rerank'",
                    status_code=404,
                    request_id="req-rerank",
                )
            )
        )
        endpoint = self.rerank_endpoint(service).endpoint
        response = await endpoint(FakeRequest(body=b'{"model": "unknown-model"}'))
        assert response.status_code == 404
        assert loads(response.body) == {
            "error": {
                "message": "no channel serves endpoint 'rerank'",
                "type": "invalid_request_error",
                "code": "MODEL_NOT_FOUND",
                "request_id": "req-rerank",
            }
        }

    async def test_rerank_missing_model_400(self) -> None:
        service = FakePassthroughService(
            Ok(RelayGatewayResult(status_code=200, headers={}, payload={}))
        )
        endpoint = self.rerank_endpoint(service).endpoint
        response = await endpoint(FakeRequest(body=b"{}"))
        assert response.status_code == 400
        assert service.calls == []

    async def test_rerank_route_registered_in_mount(self) -> None:
        service = FakePassthroughService(
            Ok(RelayGatewayResult(status_code=200, headers={}, payload={}))
        )
        routes = build_routes(
            FakeResolver(_ok_gateway()),
            resolve_passthrough=FakePassthroughResolver(service),
        )
        paths = [route.path for route in routes]
        assert "/v1/rerank" in paths

class TestModerationsRoute:
    """``POST /v1/moderations`` passthrough route behavior."""

    @staticmethod
    def moderations_endpoint(service: FakePassthrough) -> Any:
        routes = build_routes(
            FakeResolver(FakeGateway(_ok_gateway()._outcome)),
            resolve_passthrough=FakePassthroughResolver(service),
        )
        return next(r for r in routes if r.path == "/v1/moderations")

    async def test_buffered_moderations_success(self) -> None:
        payload = {
            "id": "modr-1",
            "model": "moderation-1",
            "results": [{"flagged": False, "categories": {}, "category_scores": {}}],
        }
        service = FakePassthroughService(
            Ok(RelayGatewayResult(status_code=200, headers={}, payload=payload))
        )
        endpoint = self.moderations_endpoint(service).endpoint
        response = await endpoint(
            FakeRequest(
                body=b'{"model": "moderation-1", "input": "hi"}',
                request_id="req-mod",
                user={"id": "u1", "tenant_id": "t1"},
            )
        )
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert loads(response.body) == payload
        assert response.headers.get("x-request-id") == "req-mod"
        kind, request = service.calls[0]
        assert kind == "moderation"
        assert request.request_id == "req-mod"
        assert request.tenant_id == "t1"
        assert request.model == "moderation-1"
        assert request.source is RelayFormat.OPENAI_CHAT
        assert request.stream is False
        assert request.channel is None
        assert request.payload == {"model": "moderation-1", "input": "hi"}

    async def test_moderations_error_uses_openai_envelope(self) -> None:
        service = FakePassthroughService(
            Err(
                RelayGatewayError(
                    code="MODEL_NOT_FOUND",
                    message="no channel serves endpoint 'moderation'",
                    status_code=404,
                    request_id="req-mod",
                )
            )
        )
        endpoint = self.moderations_endpoint(service).endpoint
        response = await endpoint(FakeRequest(body=b'{"model": "unknown-model"}'))
        assert response.status_code == 404
        assert loads(response.body) == {
            "error": {
                "message": "no channel serves endpoint 'moderation'",
                "type": "invalid_request_error",
                "code": "MODEL_NOT_FOUND",
                "request_id": "req-mod",
            }
        }

    async def test_moderations_missing_model_400(self) -> None:
        service = FakePassthroughService(
            Ok(RelayGatewayResult(status_code=200, headers={}, payload={}))
        )
        endpoint = self.moderations_endpoint(service).endpoint
        response = await endpoint(FakeRequest(body=b"{}"))
        assert response.status_code == 400
        assert service.calls == []

    async def test_moderations_route_registered_in_mount(self) -> None:
        service = FakePassthroughService(
            Ok(RelayGatewayResult(status_code=200, headers={}, payload={}))
        )
        routes = build_routes(
            FakeResolver(_ok_gateway()),
            resolve_passthrough=FakePassthroughResolver(service),
        )
        paths = [route.path for route in routes]
        assert "/v1/moderations" in paths
        assert paths[-1] == "/v1/images/edits"

    async def test_audio_and_image_routes_registered_in_mount(self) -> None:
        service = FakePassthroughService(
            Ok(RelayGatewayResult(status_code=200, headers={}, payload={}))
        )
        routes = build_routes(
            FakeResolver(_ok_gateway()),
            resolve_passthrough=FakePassthroughResolver(service),
        )
        paths = [route.path for route in routes]
        for audio_path in (
            "/v1/audio/speech",
            "/v1/audio/transcriptions",
            "/v1/audio/translations",
            "/v1/images/generations",
            "/v1/images/edits",
        ):
            assert audio_path in paths, f"{audio_path} not mounted"
            assert audio_path in RELAY_ROUTE_PATHS, f"{audio_path} missing from RELAY_ROUTE_PATHS"

