from typing import Any

from lexigram.ai.relay.gateway.job_registry import RelayJobRegistry
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
)
from lexigram.contracts.core.result import Err

KIND = "video_generation"
MODEL = "video-gen-1"
REQUEST_ID = "req-123"
TENANT_ID = "tenant-1"
BASE_URL = "https://upstream.example.com"
SUBMIT_BODY = {
    "model": MODEL,
    "prompt": "a cat on a skateboard",
    "size": "1024x1024",
}
UPSTREAM_JOB_ID = "video-42"
UPSTREAM_RESPONSE = {
    "id": UPSTREAM_JOB_ID,
    "object": "video",
    "status": "succeeded",
}

from ._test_job_passthrough_support import (
    FakeClock,
    RecordingAuthorizer,
    RecordingBilling,
    RequestCapturingUpstream,
    make_channel,
    make_request,
    make_service,
    ok_upstream,
)


class TestStatus:
    """Status lifecycle: same-channel routing, id rewrite, authorize-only."""

    async def test_status_routes_to_same_channel_and_rewrites_id(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(calls)
        billing = RecordingBilling(calls)
        service = make_service(
            calls,
            channels=(
                make_channel("a", priority=1),
                make_channel("b", priority=2),
            ),
            upstream=upstream,
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        submitted = await service.submit(KIND, make_request())
        assert submitted.is_ok()
        gateway_job_id = str((submitted.unwrap().payload or {})["id"])
        calls.clear()
        upstream.result = ok_upstream(
            {
                "id": UPSTREAM_JOB_ID,
                "object": "video",
                "status": "completed",
                "url": "https://cdn.example.com/video.mp4",
            }
        )
        result = await service.status(KIND, gateway_job_id, make_request())
        assert result.is_ok()
        payload = dict(result.unwrap().payload or {})
        assert payload == {
            "id": gateway_job_id,
            "object": "video",
            "status": "completed",
            "url": "https://cdn.example.com/video.mp4",
        }
        assert upstream.captured[1].channel_name == "a"
        assert upstream.captured[1].method == "GET"
        assert calls == [
            ("authorize", TENANT_ID, "relay.invoke", MODEL),
            ("upstream", f"{BASE_URL}/v1/videos/{UPSTREAM_JOB_ID}"),
        ]

    async def test_status_does_not_reselect_a_channel(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(calls, authorizer=RecordingAuthorizer(calls))
        submitted = await service.submit(KIND, make_request())
        gateway_job_id = str((submitted.unwrap().payload or {})["id"])
        calls.clear()
        result = await service.status(KIND, gateway_job_id, make_request())
        assert result.is_ok()
        assert [call[0] for call in calls] == ["authorize", "upstream"]

    async def test_status_unknown_job_is_model_not_found(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(calls)
        service = make_service(
            calls,
            upstream=upstream,
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        result = await service.status(KIND, "no-such-job", make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "MODEL_NOT_FOUND"
        assert err.status_code == 404
        assert err.request_id == REQUEST_ID
        assert upstream.captured == []
        assert [call[0] for call in calls] == ["authorize"]

    async def test_status_cross_tenant_is_same_not_found(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(calls)
        service = make_service(
            calls,
            upstream=upstream,
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        submitted = await service.submit(KIND, make_request())
        assert submitted.is_ok()
        gateway_job_id = str((submitted.unwrap().payload or {})["id"])
        calls.clear()

        other = RelayGatewayRequest(
            request_id=REQUEST_ID,
            tenant_id="tenant-2",
            source=RelayFormat.OPENAI_CHAT,
            model=MODEL,
            stream=False,
            payload={},
            headers={},
            channel=None,
        )
        result = await service.status(KIND, gateway_job_id, other)
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "MODEL_NOT_FOUND"
        assert err.status_code == 404
        assert err.request_id == REQUEST_ID
        assert [r.method for r in upstream.captured] == ["POST"]
        assert [call[0] for call in calls] == ["authorize"]

    async def test_status_expired_job_is_model_not_found(self) -> None:
        calls: list[tuple[Any, ...]] = []
        clock = FakeClock()
        job_registry = RelayJobRegistry(job_ttl_seconds=10, clock=clock)
        upstream = RequestCapturingUpstream(calls)
        service = make_service(
            calls,
            job_registry=job_registry,
            clock=clock,
            upstream=upstream,
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        submitted = await service.submit(KIND, make_request())
        gateway_job_id = str((submitted.unwrap().payload or {})["id"])
        clock.advance(11)
        calls.clear()
        upstream.captured.clear()
        result = await service.status(KIND, gateway_job_id, make_request())
        assert result.is_err()
        assert result.unwrap_err().code == "MODEL_NOT_FOUND"
        assert upstream.captured == []

    async def test_status_authorizes_without_billing(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = make_service(
            calls,
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        submitted = await service.submit(KIND, make_request())
        gateway_job_id = str((submitted.unwrap().payload or {})["id"])
        calls.clear()
        billing.settle_statuses.clear()
        billing.settle_usages.clear()
        result = await service.status(KIND, gateway_job_id, make_request())
        assert result.is_ok()
        assert [call[0] for call in calls] == ["authorize", "upstream"]
        assert billing.settle_statuses == []

    async def test_status_without_authorizer_or_billing(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(calls, authorizer=None, billing=None)
        submitted = await service.submit(KIND, make_request())
        gateway_job_id = str((submitted.unwrap().payload or {})["id"])
        calls.clear()
        result = await service.status(KIND, gateway_job_id, make_request())
        assert result.is_ok()
        assert [call[0] for call in calls] == ["upstream"]

    async def test_status_unknown_kind_is_invalid_request(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(calls)
        submitted = await service.submit(KIND, make_request())
        gateway_job_id = str((submitted.unwrap().payload or {})["id"])
        result = await service.status(
            "music_generation", gateway_job_id, make_request()
        )
        assert result.is_err()
        assert result.unwrap_err().code == "INVALID_REQUEST"

    async def test_status_upstream_error_propagates(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream_error = RelayGatewayError(
            code="UPSTREAM_FAILED",
            message="upstream transport failure",
            status_code=502,
            request_id="",
            retryable=True,
        )
        upstream = RequestCapturingUpstream(calls)
        service = make_service(
            calls,
            upstream=upstream,
            authorizer=RecordingAuthorizer(calls),
        )
        submitted = await service.submit(KIND, make_request())
        gateway_job_id = str((submitted.unwrap().payload or {})["id"])
        upstream.result = Err(upstream_error)
        calls.clear()
        result = await service.status(KIND, gateway_job_id, make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "UPSTREAM_FAILED"
        assert err.status_code == 502
        assert err.request_id == REQUEST_ID

    async def test_status_malformed_upstream_body_maps_to_502(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(calls)
        service = make_service(calls, upstream=upstream)
        submitted = await service.submit(KIND, make_request())
        gateway_job_id = str((submitted.unwrap().payload or {})["id"])
        calls.clear()
        upstream.result = ok_upstream(None)
        result = await service.status(KIND, gateway_job_id, make_request())
        assert result.is_err()
        assert result.unwrap_err().code == "UPSTREAM_MALFORMED"

    async def test_status_channel_removed_between_submit_and_status(self) -> None:
        calls: list[tuple[Any, ...]] = []
        clock = FakeClock()
        first = make_service(calls, clock=clock)
        submitted = await first.submit(KIND, make_request())
        gateway_job_id = str((submitted.unwrap().payload or {})["id"])
        second = make_service(
            calls,
            channels=(),
            job_registry=first.job_registry,
        )
        result = await second.status(KIND, gateway_job_id, make_request())
        assert result.is_err()
        assert result.unwrap_err().code == "MODEL_NOT_FOUND"

    async def test_status_unexpected_exception_wrapped_safe(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(calls)
        service = make_service(calls, upstream=upstream)
        submitted = await service.submit(KIND, make_request())
        gateway_job_id = str((submitted.unwrap().payload or {})["id"])
        calls.clear()
        upstream.error = RuntimeError("boom")
        result = await service.status(KIND, gateway_job_id, make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "CONVERSION_FAILED"
        assert err.status_code == 500
        assert err.request_id == REQUEST_ID
