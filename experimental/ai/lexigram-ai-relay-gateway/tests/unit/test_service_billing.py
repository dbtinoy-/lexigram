"""Relay gateway billing lifecycle and upstream retry tests.

Verifies billing admission (``QUOTA_EXCEEDED``, ``BILLING_FAILED``),
settlement statuses (completed/failed), reservation release on short
circuits, and the retry loop that re-enters billing per attempt.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.service import RelayGatewayService
from lexigram.contracts.ai.governance import (
    RelayBillingError,
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    OpenAIChatResponse,
    RelayFormat,
    RelayGatewayError,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.core.result import Err, Result
from service_test_helpers import (
    MODEL,
    REQUEST_ID,
    RecordingAuthorizer,
    RecordingBilling,
    RecordingConverter,
    RecordingRegistry,
    RecordingUpstream,
    claude_request_dto,
    claude_response_wire,
    happy_service,
    make_channel,
    make_request,
    make_service,
    ok_request_result,
    ok_response_result,
    ok_upstream,
)


class DenyingBilling(RecordingBilling):
    """Billing double that denies admission with a configurable code."""

    def __init__(self, calls: list[tuple[Any, ...]], *, code: str) -> None:
        super().__init__(calls, admit=False)
        self.deny_code = code

    async def pre_consume(
        self,
        request_id: str,
        scope: RelayUsageScope,
        payload: Any,
    ) -> Any:
        """Record the attempt and deny with the configured error code."""
        self.calls.append(("pre_consume", scope.tenant_id, scope.channel))
        return Err(
            RelayBillingError(
                code=self.deny_code,
                message="billing failure",
                request_id=request_id,
                tenant_id=scope.tenant_id,
            )
        )


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


class SequencedUpstream:
    """Upstream double returning canned results in call order."""

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        results: list[Result[UpstreamResponse, RelayGatewayError]],
    ) -> None:
        self.calls = calls
        self.results = list(results)

    async def request(
        self, request: UpstreamRequest
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Record the call and pop the next canned result."""
        self.calls.append(("upstream", request.channel_name))
        if not self.results:
            raise AssertionError("SequencedUpstream exhausted its results")
        return self.results.pop(0)


RETRYABLE_ERROR = RelayGatewayError(
    code="UPSTREAM_FAILED",
    message="upstream unavailable",
    status_code=502,
    request_id="",
    retryable=True,
)

NON_RETRYABLE_ERROR = RelayGatewayError(
    code="UPSTREAM_ERROR",
    message="bad request upstream",
    status_code=400,
    request_id="",
    retryable=False,
)


def retry_service(
    calls: list[tuple[Any, ...]],
    *,
    upstream: RecordingUpstream | SequencedUpstream,
    max_upstream_retries: int,
    billing: RecordingBilling | None = None,
) -> RelayGatewayService:
    """Assemble a service over two equal channels with a configurable budget."""
    converter = RecordingConverter(
        calls,
        request_result=ok_request_result(claude_request_dto(), RelayFormat.CLAUDE),
        response_result=ok_response_result(
            OpenAIChatResponse.from_dict({"id": "resp-1", "model": "m"}),
            RelayFormat.CLAUDE,
        ),
    )
    config = RelayGatewayConfig(
        channels=(make_channel("a"), make_channel("b")),
        max_upstream_retries=max_upstream_retries,
    )
    return RelayGatewayService(
        converter=converter,
        codec=RelayPayloadCodec(),
        registry=RecordingRegistry(config, calls),
        upstream=upstream,  # type: ignore[arg-type]
        config=config,
        authorizer=RecordingAuthorizer(calls),
        billing=billing,
    )


class TestBillingLifecycle:
    """Billing admission and settlement around the buffered pipeline."""

    @pytest.mark.asyncio
    async def test_billing_denial_fails_before_upstream(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls=calls,
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls, admit=False),
        )
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "QUOTA_EXCEEDED"
        assert err.status_code == 429
        assert err.retryable is True
        assert err.request_id == REQUEST_ID
        assert [call[0] for call in calls] == [
            "authorize",
            "select",
            "pre_consume",
        ]
        assert "upstream" not in [call[0] for call in calls]

    @pytest.mark.asyncio
    async def test_billing_other_error_maps_to_billing_failed(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = DenyingBilling(calls, code="unknown_price")
        service = make_service(
            calls=calls,
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "BILLING_FAILED"
        assert err.status_code == 500
        assert err.retryable is False

    @pytest.mark.asyncio
    async def test_success_settles_completed_once(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = happy_service(calls)
        result = await service.handle(make_request())
        assert result.is_ok()
        assert calls.count(("settle", "completed")) == 1

    @pytest.mark.asyncio
    async def test_settle_failure_never_fails_the_response(self) -> None:
        calls: list[tuple[Any, ...]] = []
        converter = RecordingConverter(
            calls,
            request_result=ok_request_result(claude_request_dto(), RelayFormat.CLAUDE),
            response_result=ok_response_result(
                OpenAIChatResponse.from_dict({"id": "resp-1", "model": "m"}),
                RelayFormat.CLAUDE,
            ),
        )
        service = make_service(
            calls=calls,
            converter=converter,
            upstream=RecordingUpstream(
                calls, result=ok_upstream(claude_response_wire())
            ),
            authorizer=RecordingAuthorizer(calls),
            billing=FailingSettling(calls),
        )
        result = await service.handle(make_request())
        assert result.is_ok()
        assert ("settle", "completed") in calls


class TestUpstreamRetry:
    """Retry loop: retryable failures retry across channels within budget."""

    @pytest.mark.asyncio
    async def test_retryable_failure_retries_and_returns_second_success(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = SequencedUpstream(
            calls, [Err(RETRYABLE_ERROR), ok_upstream(claude_response_wire())]
        )
        service = retry_service(calls, upstream=upstream, max_upstream_retries=1)
        result = await service.handle(make_request())
        assert result.is_ok()
        channels = [call[1] for call in calls if call[0] == "upstream"]
        assert channels == ["a", "b"]
        assert len([call for call in calls if call[0] == "select"]) == 2

    @pytest.mark.asyncio
    async def test_non_retryable_failure_never_retries(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RecordingUpstream(calls, result=Err(NON_RETRYABLE_ERROR))
        billing = RecordingBilling(calls)
        service = retry_service(
            calls, upstream=upstream, max_upstream_retries=2, billing=billing
        )
        result = await service.handle(make_request())
        assert result.is_err()
        assert result.unwrap_err().code == "UPSTREAM_ERROR"
        assert len([call for call in calls if call[0] == "upstream"]) == 1
        assert [call for call in calls if call[0] == "select"] == [
            ("select", MODEL, False, None)
        ]
        assert billing.settle_statuses == ["failed"]

    @pytest.mark.asyncio
    async def test_default_zero_budget_reproduces_single_attempt(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RecordingUpstream(calls, result=Err(RETRYABLE_ERROR))
        billing = RecordingBilling(calls)
        service = retry_service(
            calls, upstream=upstream, max_upstream_retries=0, billing=billing
        )
        result = await service.handle(make_request())
        assert result.is_err()
        assert result.unwrap_err().code == "UPSTREAM_FAILED"
        assert len([call for call in calls if call[0] == "upstream"]) == 1
        assert billing.settle_statuses == ["failed"]

    @pytest.mark.asyncio
    async def test_exhausted_channels_return_last_real_error(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = SequencedUpstream(
            calls, [Err(RETRYABLE_ERROR), Err(RETRYABLE_ERROR)]
        )
        billing = RecordingBilling(calls)
        service = retry_service(
            calls, upstream=upstream, max_upstream_retries=3, billing=billing
        )
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "UPSTREAM_FAILED"
        assert len([call for call in calls if call[0] == "upstream"]) == 2
        assert billing.settle_statuses == ["failed"]

    @pytest.mark.asyncio
    async def test_failed_attempt_reservation_released_before_retry(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = SequencedUpstream(
            calls, [Err(RETRYABLE_ERROR), ok_upstream(claude_response_wire())]
        )
        billing = RecordingBilling(calls)
        service = retry_service(
            calls, upstream=upstream, max_upstream_retries=1, billing=billing
        )
        result = await service.handle(make_request())
        assert result.is_ok()
        assert billing.release_count == 1
        assert billing.settle_statuses == ["completed"]
        pre_consumes = [call for call in calls if call[0] == "pre_consume"]
        assert len(pre_consumes) == 2

    @pytest.mark.asyncio
    async def test_retry_emits_structured_event_per_attempt(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = SequencedUpstream(
            calls, [Err(RETRYABLE_ERROR), ok_upstream(claude_response_wire())]
        )
        service = retry_service(calls, upstream=upstream, max_upstream_retries=1)
        from structlog.testing import capture_logs

        with capture_logs() as cap:
            await service.handle(make_request())
        retries = [e for e in cap if e.get("event") == "relay_gateway_upstream_retry"]
        assert len(retries) == 1
        assert retries[0]["channel"] == "a"
        assert retries[0]["error_code"] == "UPSTREAM_FAILED"
        assert retries[0]["attempt"] == 1
