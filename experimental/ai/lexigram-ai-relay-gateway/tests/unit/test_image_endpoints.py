"""Image passthrough endpoint tests (Relay Gateway Plan, image endpoints).

Covers the raw Starlette image routes (``build_image_routes``) for
``POST /v1/images/generations`` and ``POST /v1/images/edits``: JSON
generations bodies forward decoded like the embeddings route, multipart
edits bodies forward byte-for-byte with the ``model`` form field lifted
into the gateway request, and upstream responses pass through verbatim
— JSON as JSON, binary bodies on the wire unchanged — with errors
rendered in the OpenAI error envelope.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from starlette.responses import JSONResponse, Response

from lexigram.ai.relay.gateway.passthrough import RelayPassthroughResult
from lexigram.ai.relay.gateway.web.image_endpoints import (
    IMAGE_ROUTE_PATHS,
    build_image_routes,
)
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayGatewayResult,
)
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.serialization import loads

KIND_GENERATIONS = "image_generation"
KIND_EDITS = "image_edit"
MODEL = "dall-e-3"
REQUEST_ID = "req-img"
TENANT_ID = "tenant-1"

MULTIPART_BOUNDARY = "bnd-42"
MULTIPART_CONTENT_TYPE = f"multipart/form-data; boundary={MULTIPART_BOUNDARY}"
MULTIPART_BODY = b"".join(
    [
        f"--{MULTIPART_BOUNDARY}\r\n".encode("ascii"),
        b'Content-Disposition: form-data; name="model"\r\n',
        b"\r\n",
        MODEL.encode("ascii"),
        b"\r\n",
        f"--{MULTIPART_BOUNDARY}\r\n".encode("ascii"),
        b'Content-Disposition: form-data; name="image"; filename="starry.png"\r\n',
        b"Content-Type: image/png\r\n",
        b"\r\n",
        b"\x89PNG\r\n\x1a\nBINARY\x00\xffDATA",
        b"\r\n",
        f"--{MULTIPART_BOUNDARY}--\r\n".encode("ascii"),
    ]
)
"""A two-part edits body: a ``model`` field plus a binary ``image`` part."""

BINARY_IMAGE = b"\x89PNG\r\n\x1a\nRELAYED\x00\xffIMAGE"


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
        headers: dict[str, str] | None = None,
    ) -> None:
        self._body = body
        self.state = SimpleNamespace(request_id=request_id, user=user, container=None)
        self.method = "POST"
        self.headers: dict[str, str] = headers if headers is not None else {}

    async def body(self) -> bytes:
        """Return the canned request body."""
        return self._body


def _ok_result(payload: dict[str, Any]) -> FakePassthroughService:
    """A passthrough service returning one decoded JSON payload."""
    return FakePassthroughService(
        Ok(
            RelayGatewayResult(
                status_code=200,
                headers={"content-type": "application/json"},
                payload=payload,
            )
        )
    )


def image_route(path: str, service: FakePassthroughService) -> Any:
    """The built route for *path* bound to *service*."""
    routes = build_image_routes(FakePassthroughResolver(service))
    return next(route for route in routes if route.path == path)


class TestImageGenerationsRoute:
    """``POST /v1/images/generations`` JSON passthrough behavior."""

    async def test_buffered_generations_success(self) -> None:
        payload = {
            "created": 1720000000,
            "data": [{"url": "https://upstream.example.com/img.png"}],
        }
        service = _ok_result(payload)
        endpoint = image_route("/v1/images/generations", service).endpoint
        response = await endpoint(
            FakeRequest(
                body=b'{"model": "dall-e-3", "prompt": "a starry night", "n": 1}',
                request_id=REQUEST_ID,
                user={"id": "u1", "tenant_id": TENANT_ID},
            )
        )
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert loads(response.body) == payload
        assert response.headers.get("x-request-id") == REQUEST_ID
        kind, request = service.calls[0]
        assert kind == KIND_GENERATIONS
        assert request.request_id == REQUEST_ID
        assert request.tenant_id == TENANT_ID
        assert request.model == MODEL
        assert request.source is RelayFormat.OPENAI_CHAT
        assert request.stream is False
        assert request.channel is None
        assert request.payload == {
            "model": MODEL,
            "prompt": "a starry night",
            "n": 1,
        }

    async def test_generations_error_uses_openai_envelope(self) -> None:
        service = FakePassthroughService(
            Err(
                RelayGatewayError(
                    code="MODEL_NOT_FOUND",
                    message="no channel serves endpoint 'image_generation'",
                    status_code=404,
                    request_id=REQUEST_ID,
                )
            )
        )
        endpoint = image_route("/v1/images/generations", service).endpoint
        response = await endpoint(FakeRequest(body=b'{"model": "unknown"}'))
        assert response.status_code == 404
        assert loads(response.body) == {
            "error": {
                "message": "no channel serves endpoint 'image_generation'",
                "type": "invalid_request_error",
                "code": "MODEL_NOT_FOUND",
                "request_id": REQUEST_ID,
            }
        }

    async def test_generations_missing_model_400(self) -> None:
        service = _ok_result({})
        endpoint = image_route("/v1/images/generations", service).endpoint
        response = await endpoint(FakeRequest(body=b"{}"))
        assert response.status_code == 400
        assert service.calls == []

    async def test_generations_malformed_body_400(self) -> None:
        service = _ok_result({})
        endpoint = image_route("/v1/images/generations", service).endpoint
        response = await endpoint(FakeRequest(body=b"not json"))
        assert response.status_code == 400
        assert service.calls == []


class TestImageEditsRoute:
    """``POST /v1/images/edits`` multipart passthrough behavior."""

    @staticmethod
    def edits_endpoint(service: FakePassthroughService) -> Any:
        return image_route("/v1/images/edits", service).endpoint

    async def test_multipart_edits_forwarded_verbatim(self) -> None:
        payload = {
            "created": 1720000000,
            "data": [{"url": "http://upstream.example.com/edited.png"}],
        }
        service = _ok_result(payload)
        endpoint = self.edits_endpoint(service)
        response = await endpoint(
            FakeRequest(
                body=MULTIPART_BODY,
                request_id=REQUEST_ID,
                user={"id": "u1", "tenant_id": TENANT_ID},
                headers={"content-type": MULTIPART_CONTENT_TYPE},
            )
        )
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert loads(response.body) == payload
        kind, request = service.calls[0]
        assert kind == KIND_EDITS
        assert request.request_id == REQUEST_ID
        assert request.tenant_id == TENANT_ID
        assert request.model == MODEL
        assert request.source is RelayFormat.OPENAI_CHAT
        assert request.stream is False
        assert request.channel is None
        assert request.payload.data == MULTIPART_BODY
        assert request.payload.content_type == MULTIPART_CONTENT_TYPE

    async def test_multipart_edits_binary_response_passthrough(self) -> None:
        service = FakePassthroughService(
            Ok(
                RelayPassthroughResult(
                    status_code=200,
                    headers={"content-type": "image/png"},
                    body=BINARY_IMAGE,
                    content_type="image/png",
                )
            )
        )
        endpoint = self.edits_endpoint(service)
        response = await endpoint(
            FakeRequest(
                body=MULTIPART_BODY,
                request_id=REQUEST_ID,
                headers={"content-type": MULTIPART_CONTENT_TYPE},
            )
        )
        assert isinstance(response, Response)
        assert response.status_code == 200
        assert response.body == BINARY_IMAGE
        assert response.headers.get("content-type") == "image/png"
        assert response.headers.get("x-request-id") == REQUEST_ID

    async def test_multipart_edits_missing_model_400(self) -> None:
        service = _ok_result({})
        body_without_model = MULTIPART_BODY.replace(
            b'Content-Disposition: form-data; name="model"\r\n\r\n'
            + MODEL.encode("ascii")
            + b"\r\n",
            b"",
            1,
        )
        endpoint = self.edits_endpoint(service)
        response = await endpoint(
            FakeRequest(
                body=body_without_model,
                headers={"content-type": MULTIPART_CONTENT_TYPE},
            )
        )
        assert response.status_code == 400
        assert service.calls == []

    async def test_multipart_edits_without_boundary_400(self) -> None:
        service = _ok_result({})
        endpoint = self.edits_endpoint(service)
        response = await endpoint(
            FakeRequest(
                body=MULTIPART_BODY,
                headers={"content-type": "multipart/form-data"},
            )
        )
        assert response.status_code == 400
        assert service.calls == []


class TestImageRoutes:
    """Route registration of the image endpoints."""

    def test_build_image_routes_registers_both_paths(self) -> None:
        service = _ok_result({})
        routes = build_image_routes(FakePassthroughResolver(service))
        assert [route.path for route in routes] == [
            "/v1/images/generations",
            "/v1/images/edits",
        ]
        for route in routes:
            assert route.methods == {"POST"}
        assert IMAGE_ROUTE_PATHS == ("/v1/images/generations", "/v1/images/edits")
