"""Video job passthrough routes: submit and status polling."""

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

from web_test_helpers import (
    FakeJobPassthroughResolver,
    FakeJobPassthroughService,
    FakePassthroughResolver,
    FakeRequest,
    FakeResolver,
    _ok_gateway,
)


class TestVideoRoutes:
    """Job-relay routes: ``POST /v1/videos`` and ``GET /v1/videos/{job_id}``."""

    @staticmethod
    def video_routes(
        service: FakeJobPassthroughService,
    ) -> list[Any]:
        routes = build_routes(
            FakeResolver(_ok_gateway()),
            resolve_passthrough=FakePassthroughResolver(service),
            resolve_job_passthrough=FakeJobPassthroughResolver(service),
        )
        return routes

    async def test_video_submit_route_calls_job_passthrough(self) -> None:
        """POST /v1/videos forwards the body and returns the JSON verbatim."""
        payload = {
            "id": "00000000-0000-0000-0000-000000000001",
            "object": "video",
            "status": "succeeded",
        }
        service = FakeJobPassthroughService(
            submit_outcome=Ok(
                RelayGatewayResult(status_code=200, headers={}, payload=payload)
            )
        )
        routes = self.video_routes(service)
        submit_route = next(route for route in routes if route.path == "/v1/videos")
        response = await submit_route.endpoint(
            FakeRequest(
                body=b'{"model": "video-gen-1", "prompt": "a cat"}',
                request_id="req-vid",
                user={"id": "u1", "tenant_id": "t1"},
            )
        )
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert loads(response.body) == payload
        assert response.headers.get("x-request-id") == "req-vid"
        kind, request = service.submit_calls[0]
        assert kind == "video_generation"
        assert request.request_id == "req-vid"
        assert request.tenant_id == "t1"
        assert request.model == "video-gen-1"
        assert request.source is RelayFormat.OPENAI_CHAT
        assert request.stream is False
        assert request.channel is None
        assert request.payload == {"model": "video-gen-1", "prompt": "a cat"}
        service._submit_outcome = Err(
            RelayGatewayError(
                code="MODEL_NOT_FOUND",
                message="no relay job found for the given id",
                status_code=404,
                request_id="req-vid",
            )
        )
        error_response = await submit_route.endpoint(
            FakeRequest(
                body=b'{"model": "video-gen-1", "prompt": "a cat"}',
                request_id="req-vid",
            )
        )
        assert error_response.status_code == 404
        assert loads(error_response.body) == {
            "error": {
                "message": "no relay job found for the given id",
                "type": "invalid_request_error",
                "code": "MODEL_NOT_FOUND",
                "request_id": "req-vid",
            }
        }

    async def test_video_status_route_polls_same_job(self) -> None:
        """GET /v1/videos/{job_id} calls ``status`` and returns the JSON verbatim."""
        payload = {
            "id": "00000000-0000-0000-0000-000000000001",
            "object": "video",
            "status": "completed",
            "url": "https://cdn.example.com/video.mp4",
        }
        service = FakeJobPassthroughService(
            status_outcome=Ok(
                RelayGatewayResult(status_code=200, headers={}, payload=payload)
            )
        )
        routes = self.video_routes(service)
        status_route = next(
            route for route in routes if route.path == "/v1/videos/{job_id}"
        )
        response = await status_route.endpoint(
            FakeRequest(
                body=b"",
                path_params={"job_id": "job-1"},
                request_id="req-vid",
                user={"id": "u1", "tenant_id": "t1"},
            )
        )
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert loads(response.body) == payload
        assert response.headers.get("x-request-id") == "req-vid"
        kind, job_id, request = service.status_calls[0]
        assert kind == "video_generation"
        assert job_id == "job-1"
        assert request.request_id == "req-vid"
        assert request.tenant_id == "t1"
        assert request.model == ""
        assert request.stream is False
        assert request.payload == {}
        service._status_outcome = Err(
            RelayGatewayError(
                code="AUTH_DENIED",
                message="denied",
                status_code=403,
                request_id="req-vid",
            )
        )
        error_response = await status_route.endpoint(
            FakeRequest(
                body=b"",
                path_params={"job_id": "job-1"},
                request_id="req-vid",
            )
        )
        assert error_response.status_code == 403
        assert loads(error_response.body)["error"]["type"] == "permission_denied_error"

