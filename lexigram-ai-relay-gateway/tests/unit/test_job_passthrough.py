"""Job passthrough service tests (Plan N, Task 2).

Verifies the job-relay lifecycle of ``JobPassthroughService`` for video
generation: channel selection and credential injection on submit,
channel-affinity on status polls, gateway-issued id rewriting in both
directions, billing-on-submit-only, and the not-found error family for
unknown and expired job ids.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import time
from typing import Any

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.job_passthrough import JobPassthroughService
from lexigram.ai.relay.gateway.job_registry import RelayJobRegistry
from lexigram.contracts.ai.governance import (
    RelayBillingError,
    RelayUsageRecord,
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    RelayChannel,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayUsage,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.core.result import Err, Ok, Result

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


def make_channel(name: str = "a", **overrides: Any) -> RelayChannel:
    """Build a video-capable channel with defaults; ``overrides`` win."""
    defaults: dict[str, Any] = {
        "name": name,
        "upstream_base_url": BASE_URL,
        "target_format": RelayFormat.OPENAI_CHAT,
        "models": (MODEL,),
        "endpoint_kinds": frozenset({KIND}),
    }
    defaults.update(overrides)
    return RelayChannel(**defaults)


def default_channels() -> tuple[RelayChannel, ...]:
    """One enabled video channel plus one disabled channel."""
    return (make_channel("a"), make_channel("b", enabled=False))


def make_request(
    model: str = MODEL,
    payload: dict[str, Any] | None = None,
    channel: RelayChannel | None = None,
) -> RelayGatewayRequest:
    """Build a job-submit ``RelayGatewayRequest`` with a video body."""
    return RelayGatewayRequest(
        request_id=REQUEST_ID,
        tenant_id=TENANT_ID,
        source=RelayFormat.OPENAI_CHAT,
        model=model,
        stream=False,
        payload=payload if payload is not None else dict(SUBMIT_BODY),
        headers={},
        channel=channel,
    )


def ok_upstream(
    payload: dict[str, Any] | None,
    status_code: int = 200,
) -> Result[UpstreamResponse, RelayGatewayError]:
    """A canned Ok upstream result."""
    return Ok(
        UpstreamResponse(
            status_code=status_code,
            headers={"content-type": "application/json"},
            payload=payload,
        )
    )


class FakeClock:
    """Monotonic clock double whose value tests advance explicitly."""

    def __init__(self, now: float = 0.0) -> None:
        self._now = now

    def __call__(self) -> float:
        """Return the configured monotonic time."""
        return self._now

    def advance(self, seconds: float) -> None:
        """Advance the fake time by *seconds*."""
        self._now += seconds


class RecordingRegistry(RelayChannelRegistry):
    """``RelayChannelRegistry`` double that records ``select_for_endpoint`` calls."""

    def __init__(
        self, config: RelayGatewayConfig, calls: list[tuple[Any, ...]]
    ) -> None:
        super().__init__(config)
        self.calls = calls

    def select_for_endpoint(
        self,
        kind: str,
        model: str,
        *,
        exclude: frozenset[str] = frozenset(),
    ) -> Result[RelayChannel, RelayGatewayError]:
        """Record the call and delegate to the real selection logic."""
        self.calls.append(("select_endpoint", kind, model))
        return super().select_for_endpoint(kind, model, exclude=exclude)


class RecordingAuthorizer:
    """``AuthorizerProtocol`` double that records ``authorize`` calls."""

    def __init__(self, calls: list[tuple[Any, ...]], allowed: bool = True) -> None:
        self.calls = calls
        self.allowed = allowed

    async def authorize(self, user: Any, action: str, resource: Any) -> bool:
        """Record the call and return the configured verdict."""
        self.calls.append(("authorize", user, action, resource))
        return self.allowed


class RequestCapturingUpstream:
    """``HTTPUpstreamAdapter`` double that records upstream calls."""

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        *,
        result: Result[UpstreamResponse, RelayGatewayError] | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.calls = calls
        self.result = result
        self.error = error
        self.captured: list[UpstreamRequest] = []

    async def request(
        self, request: UpstreamRequest
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Record the request; return the canned result or raise the error."""
        self.calls.append(("upstream", request.url))
        self.captured.append(request)
        if self.error is not None:
            raise self.error
        if self.result is not None:
            return self.result
        return ok_upstream(dict(UPSTREAM_RESPONSE))


class RecordingBilling:
    """``RelayBillingProtocol`` double recording lifecycle invocations."""

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        *,
        admit: bool = True,
    ) -> None:
        self.calls = calls
        self.admit = admit
        self.settle_statuses: list[str] = []
        self.settle_usages: list[RelayUsage | None] = []

    async def pre_consume(
        self,
        request_id: str,
        scope: RelayUsageScope,
        payload: Any,
    ) -> Any:
        """Record the admission attempt; return the canned reservation."""
        self.calls.append(("pre_consume", scope.tenant_id, scope.channel))
        if not self.admit:
            return Err(
                RelayBillingError(
                    code="quota_exhausted",
                    message="quota exhausted",
                    request_id=request_id,
                    tenant_id=scope.tenant_id,
                )
            )
        return Ok(
            RelayUsageReservation(
                reservation_id=f"res-{request_id}",
                request_id=request_id,
                estimated_tokens=10,
                estimated_charge=Decimal("0.01"),
                expires_at=datetime.now(UTC) + timedelta(seconds=60),
            )
        )

    async def settle(
        self,
        reservation: RelayUsageReservation,
        result: Any,
        *,
        status: str,
    ) -> Any:
        """Record the settlement status and usage; return a canned record."""
        self.calls.append(("settle", status))
        self.settle_statuses.append(status)
        self.settle_usages.append(result.usage)
        return Ok(
            RelayUsageRecord(
                request_id=reservation.request_id,
                attempt_id="attempt-1",
                scope=RelayUsageScope(tenant_id="tenant-1"),
                usage=RelayUsage(),
                charge=Decimal(0),
                currency="USD",
                status=status,
            )
        )

    async def release(self, reservation: RelayUsageReservation) -> None:
        """Record the release of a reservation."""
        self.calls.append(("release", reservation.request_id))


class FailingSettling(RecordingBilling):
    """Billing double whose settlement always fails."""

    async def settle(
        self,
        reservation: RelayUsageReservation,
        result: Any,
        *,
        status: str,
    ) -> Any:
        """Record the attempt and return a billing error."""
        self.calls.append(("settle", status))
        self.settle_statuses.append(status)
        return Err(
            RelayBillingError(
                code="billing_store_unavailable",
                message="store unavailable",
                request_id=reservation.request_id,
            )
        )


def make_service(
    calls: list[tuple[Any, ...]],
    *,
    channels: tuple[RelayChannel, ...] | None = None,
    model_suffix: dict[str, str] | None = None,
    job_registry: RelayJobRegistry | None = None,
    clock: FakeClock | None = None,
    upstream: RequestCapturingUpstream | None = None,
    authorizer: RecordingAuthorizer | None = None,
    billing: RecordingBilling | None = None,
) -> JobPassthroughService:
    """Assemble a job passthrough service wired to recording doubles."""
    config = RelayGatewayConfig(
        channels=channels if channels is not None else default_channels(),
        model_suffix=model_suffix or {},
        job_ttl_seconds=10,
    )
    if job_registry is None:
        job_registry = RelayJobRegistry(
            job_ttl_seconds=10,
            clock=clock if clock is not None else FakeClock(),
        )
    return JobPassthroughService(
        registry=RecordingRegistry(config, calls),
        job_registry=job_registry,
        upstream=upstream or RequestCapturingUpstream(calls),
        config=config,
        authorizer=authorizer,
        billing=billing,
        clock=clock if clock is not None else time.monotonic,
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
        assert upstream.captured[0].payload == {**SUBMIT_BODY, "extra": {"nested": True}}

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
        result = await service.status("music_generation", gateway_job_id, make_request())
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