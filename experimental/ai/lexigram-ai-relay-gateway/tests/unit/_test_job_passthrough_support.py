"""Shared fixtures/stubs for test_job_passthrough tests."""

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


__all__ = [
    "FailingSettling",
    "FakeClock",
    "RecordingAuthorizer",
    "RecordingBilling",
    "RecordingRegistry",
    "RequestCapturingUpstream",
    "default_channels",
    "make_channel",
    "make_request",
    "make_service",
    "ok_upstream",
]
