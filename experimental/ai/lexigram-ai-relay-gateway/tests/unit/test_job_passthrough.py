from typing import Any

from lexigram.contracts.ai.relay import (
    RelayGatewayError,
    RelayUsage,
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
    FailingSettling,
    FakeClock,
    RecordingAuthorizer,
    RecordingBilling,
    RequestCapturingUpstream,
    make_channel,
    make_request,
    make_service,
    ok_upstream,
)


class TestSubmit:
    """Submit lifecycle: selection, forwarding, id rewrite, billing-once."""

    async def test_submit_selects_channel_and_rewrites_id(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(calls)
        billing = RecordingBilling(calls)
        service = make_service(
            calls,
            upstream=upstream,
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.submit(KIND, make_request())
        assert result.is_ok()
        payload = dict(result.unwrap().payload or {})
        gateway_job_id = payload["id"]
        assert payload == {
            "id": gateway_job_id,
            "object": "video",
            "status": "succeeded",
        }
        assert gateway_job_id != UPSTREAM_JOB_ID
        assert len(gateway_job_id) == 36
        captured = upstream.captured[0]
        assert captured.url == f"{BASE_URL}/v1/videos"
        assert captured.method == "POST"
        assert captured.channel_name == "a"
        assert captured.payload == dict(SUBMIT_BODY)
        assert calls == [
            ("authorize", TENANT_ID, "relay.invoke", MODEL),
            ("select_endpoint", KIND, MODEL),
            ("pre_consume", TENANT_ID, "a"),
            ("upstream", f"{BASE_URL}/v1/videos"),
            ("settle", "completed"),
        ]
        assert billing.settle_statuses == ["completed"]

    async def test_submit_stores_channel_affinity_record(self) -> None:
        calls: list[tuple[Any, ...]] = []
        clock = FakeClock()
        service = make_service(calls, clock=clock)
        result = await service.submit(KIND, make_request())
        assert result.is_ok()
        gateway_job_id = str((result.unwrap().payload or {})["id"])
        record = service.job_registry.get(gateway_job_id)
        assert record is not None
        assert record.channel_name == "a"
        assert record.upstream_job_id == UPSTREAM_JOB_ID
        assert record.endpoint_kind == KIND
        assert record.submitted_by == TENANT_ID
        assert record.created_at == clock()

    async def test_submit_other_fields_verbatim_and_no_payload_mutation(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(
            calls,
            result=ok_upstream(
                {
                    "id": UPSTREAM_JOB_ID,
                    "object": "video",
                    "status": "queued",
                    "progress": 0.5,
                    "links": ["https://cdn.example.com/0"],
                }
            ),
        )
        service = make_service(calls, upstream=upstream)
        body = {**SUBMIT_BODY, "extra": {"nested": True}}
        result = await service.submit(KIND, make_request(payload=body))
        assert result.is_ok()
        payload = result.unwrap().payload or {}
        assert payload["status"] == "queued"
        assert payload["progress"] == 0.5
        assert payload["links"] == ["https://cdn.example.com/0"]
        assert body == {**SUBMIT_BODY, "extra": {"nested": True}}
        assert upstream.captured[0].payload == {
            **SUBMIT_BODY,
            "extra": {"nested": True},
        }

    async def test_submit_applies_model_suffix(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(calls)
        service = make_service(calls, model_suffix={"a": ":gen"}, upstream=upstream)
        result = await service.submit(KIND, make_request())
        assert result.is_ok()
        assert upstream.captured[0].payload == {
            "model": f"{MODEL}:gen",
            "prompt": "a cat on a skateboard",
            "size": "1024x1024",
        }

    async def test_submit_without_authorizer_or_billing(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(calls, authorizer=None, billing=None)
        result = await service.submit(KIND, make_request())
        assert result.is_ok()
        assert [call[0] for call in calls] == ["select_endpoint", "upstream"]

    async def test_submit_unknown_kind_is_invalid_request(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(calls, authorizer=None)
        result = await service.submit("music_generation", make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "INVALID_REQUEST"
        assert err.status_code == 400
        assert err.request_id == REQUEST_ID
        assert calls == []

    async def test_submit_selection_failure_is_model_not_found(self) -> None:
        calls: list[tuple[Any, ...]] = []
        chat_only = (make_channel("chat", endpoint_kinds=frozenset()),)
        service = make_service(calls, channels=chat_only)
        result = await service.submit(KIND, make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "MODEL_NOT_FOUND"
        assert err.status_code == 404
        assert err.request_id == REQUEST_ID

    async def test_submit_all_channels_disabled_is_channel_disabled(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(calls, channels=(make_channel("a", enabled=False),))
        result = await service.submit(KIND, make_request())
        assert result.is_err()
        assert result.unwrap_err().code == "CHANNEL_DISABLED"

    async def test_submit_authorize_failure_short_circuits(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls,
            authorizer=RecordingAuthorizer(calls, allowed=False),
            billing=RecordingBilling(calls),
        )
        result = await service.submit(KIND, make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "AUTH_DENIED"
        assert err.status_code == 403
        assert err.request_id == REQUEST_ID
        assert [call[0] for call in calls] == ["authorize"]

    async def test_submit_billing_denial_fails_before_upstream(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls,
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls, admit=False),
        )
        result = await service.submit(KIND, make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "QUOTA_EXCEEDED"
        assert err.status_code == 429
        assert err.retryable is True
        assert [call[0] for call in calls] == [
            "authorize",
            "select_endpoint",
            "pre_consume",
        ]

    async def test_submit_missing_id_is_mapping_error(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = make_service(
            calls,
            upstream=RequestCapturingUpstream(
                calls, result=ok_upstream({"object": "video", "status": "queued"})
            ),
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.submit(KIND, make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "UPSTREAM_MALFORMED"
        assert err.status_code == 502
        assert err.request_id == REQUEST_ID
        assert service.job_registry._records == {}
        assert billing.settle_statuses == ["failed"]

    async def test_submit_non_string_id_is_mapping_error(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls,
            upstream=RequestCapturingUpstream(calls, result=ok_upstream({"id": 12345})),
            billing=RecordingBilling(calls),
        )
        result = await service.submit(KIND, make_request())
        assert result.is_err()
        assert result.unwrap_err().code == "UPSTREAM_MALFORMED"

    async def test_submit_empty_id_is_mapping_error(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls,
            upstream=RequestCapturingUpstream(calls, result=ok_upstream({"id": ""})),
        )
        result = await service.submit(KIND, make_request())
        assert result.is_err()
        assert result.unwrap_err().code == "UPSTREAM_MALFORMED"

    async def test_submit_upstream_error_settles_failed(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream_error = RelayGatewayError(
            code="UPSTREAM_TIMEOUT",
            message="upstream request timed out",
            status_code=504,
            request_id="",
            retryable=True,
        )
        billing = RecordingBilling(calls)
        service = make_service(
            calls,
            upstream=RequestCapturingUpstream(calls, result=Err(upstream_error)),
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.submit(KIND, make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "UPSTREAM_TIMEOUT"
        assert err.status_code == 504
        assert err.request_id == REQUEST_ID
        assert billing.settle_statuses == ["failed"]

    async def test_submit_malformed_upstream_body_maps_to_502(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = make_service(
            calls,
            upstream=RequestCapturingUpstream(calls, result=ok_upstream(None)),
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.submit(KIND, make_request())
        assert result.is_err()
        assert result.unwrap_err().code == "UPSTREAM_MALFORMED"
        assert billing.settle_statuses == ["failed"]

    async def test_submit_settles_completed_with_usage(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = make_service(
            calls,
            upstream=RequestCapturingUpstream(
                calls,
                result=ok_upstream(
                    {
                        "id": UPSTREAM_JOB_ID,
                        "object": "video",
                        "usage": {"prompt_tokens": 5, "total_tokens": 5},
                    }
                ),
            ),
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.submit(KIND, make_request())
        assert result.is_ok()
        assert billing.settle_statuses == ["completed"]
        assert billing.settle_usages == [RelayUsage(prompt_tokens=5)]

    async def test_submit_settle_failure_never_fails_the_response(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls,
            authorizer=RecordingAuthorizer(calls),
            billing=FailingSettling(calls),
        )
        result = await service.submit(KIND, make_request())
        assert result.is_ok()

    async def test_submit_unexpected_exception_wrapped_safe(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls,
            upstream=RequestCapturingUpstream(calls, error=RuntimeError("boom")),
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        result = await service.submit(KIND, make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "CONVERSION_FAILED"
        assert err.status_code == 500
        assert err.request_id == REQUEST_ID
