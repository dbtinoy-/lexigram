"""Relay gateway service lifecycle tests (Relay Gateway plan, Task 4).

Verifies the buffered request pipeline: dependency call ordering,
short-circuit behavior on authorize/channel/conversion failures,
upstream error normalization, preferred-channel hints, model suffixes,
and result metadata assembly of ``RelayGatewayService``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.operations.streams import RelayStreamRegistry
from lexigram.ai.relay.gateway.service import RelayGatewayService
from lexigram.contracts.ai.exceptions import RelayError, RelayErrorCode
from lexigram.contracts.ai.governance import (
    RelayBillingError,
    RelayUsageRecord,
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    ClaudeRequest,
    ConversionQuality,
    GeminiRequest,
    OpenAIChatRequest,
    RelayChannel,
    RelayConvertResult,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayLoss,
    RelayUsage,
    UpstreamChunk,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.ai.relay.dto import (
    OpenAIChatResponse,
)
from lexigram.contracts.core.result import Err, Ok, Result

SOURCE = RelayFormat.OPENAI_CHAT
MODEL = "test-model"
REQUEST_ID = "req-123"
TENANT_ID = "tenant-1"
BASE_URL = "https://upstream.example.com"


def make_channel(name: str = "a", **overrides: Any) -> RelayChannel:
    """Build a channel with defaults; ``overrides`` win."""
    defaults: dict[str, Any] = {
        "name": name,
        "upstream_base_url": BASE_URL,
        "target_format": RelayFormat.CLAUDE,
        "models": (MODEL,),
    }
    defaults.update(overrides)
    return RelayChannel(**defaults)


def default_channels() -> tuple[RelayChannel, ...]:
    """One enabled CLAUDE channel plus one disabled channel."""
    return (make_channel("a"), make_channel("b", enabled=False))


def make_request(
    source: RelayFormat = SOURCE,
    model: str = MODEL,
    stream: bool = False,
    channel: RelayChannel | None = None,
) -> RelayGatewayRequest:
    """Build a ``RelayGatewayRequest`` with an OpenAI Chat wire payload."""
    return RelayGatewayRequest(
        request_id=REQUEST_ID,
        tenant_id=TENANT_ID,
        source=source,
        model=model,
        stream=stream,
        payload=OpenAIChatRequest.from_dict({"model": model}).to_dict(),
        headers={},
        channel=channel,
    )


def ok_request_result(value: Any, target: RelayFormat) -> Result[Any, RelayError]:
    """A canned Ok ``convert_request`` result."""
    return Ok(
        RelayConvertResult(
            value=value,
            source=SOURCE,
            target=target,
            converter_id="test_converter",
            quality=ConversionQuality.GOOD,
        )
    )


def ok_response_result(
    value: Any,
    source: RelayFormat,
    *,
    losses: tuple[RelayLoss, ...] = (),
    warnings: tuple[str, ...] = (),
) -> Result[Any, RelayError]:
    """A canned Ok ``convert_response`` result."""
    return Ok(
        RelayConvertResult(
            value=value,
            source=source,
            target=SOURCE,
            converter_id="test_converter",
            quality=ConversionQuality.GOOD,
            losses=losses,
            warnings=warnings,
        )
    )


def ok_upstream(
    payload: dict[str, Any] | None,
) -> Result[UpstreamResponse, RelayGatewayError]:
    """A canned Ok upstream result."""
    return Ok(
        UpstreamResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            payload=payload,
        )
    )


def claude_request_dto() -> ClaudeRequest:
    """A minimal valid Claude request DTO for the target format family."""
    return ClaudeRequest.from_dict(
        {"model": "claude-x", "max_tokens": 1024, "messages": []}
    )


def claude_response_wire() -> dict[str, Any]:
    """A minimal valid Claude response wire dict for the target format."""
    return {
        "id": "msg-1",
        "model": "claude-x",
        "content": [{"type": "text", "text": "hi"}],
    }


class RecordingConverter:
    """Stub ``RelayConverterProtocol`` double recording calls and returning canned results."""

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        *,
        request_result: Result[Any, RelayError] | None = None,
        response_result: Result[Any, RelayError] | None = None,
    ) -> None:
        self.calls = calls
        self.request_result = request_result
        self.response_result = response_result

    def convert_request(
        self,
        payload: Any,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: Any = None,
        registry: Any = None,
    ) -> Result[Any, RelayError]:
        """Record the call and return the canned request result."""
        self.calls.append(("convert_request", source, target))
        if self.request_result is None:
            raise AssertionError("RecordingConverter needs a request_result")
        return self.request_result

    def convert_response(
        self,
        payload: Any,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: Any = None,
        registry: Any = None,
    ) -> Result[Any, RelayError]:
        """Record the call and return the canned response result."""
        self.calls.append(("convert_response", source, target))
        if self.response_result is None:
            raise AssertionError("RecordingConverter needs a response_result")
        return self.response_result


class RecordingRegistry(RelayChannelRegistry):
    """``RelayChannelRegistry`` double that records ``select`` calls."""

    def __init__(
        self, config: RelayGatewayConfig, calls: list[tuple[Any, ...]]
    ) -> None:
        super().__init__(config)
        self.calls = calls

    def select(
        self,
        source: RelayFormat,
        model: str,
        stream: bool = False,
        capabilities: frozenset[str] = frozenset(),
        preferred: str | None = None,
        exclude: frozenset[str] = frozenset(),
    ) -> Result[RelayChannel, RelayGatewayError]:
        """Record the call and delegate to the real selection logic."""
        self.calls.append(("select", model, stream, preferred))
        return super().select(
            source,
            model,
            stream=stream,
            capabilities=capabilities,
            preferred=preferred,
            exclude=exclude,
        )


class RecordingAuthorizer:
    """``AuthorizerProtocol`` double that records ``authorize`` calls."""

    def __init__(self, calls: list[tuple[Any, ...]], allowed: bool = True) -> None:
        self.calls = calls
        self.allowed = allowed

    async def authorize(self, user: Any, action: str, resource: Any) -> bool:
        """Record the call and return the configured verdict."""
        self.calls.append(("authorize", user, action, resource))
        return self.allowed


class RecordingUpstream:
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

    async def request(
        self, request: UpstreamRequest
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Record the call; return the canned result or raise the error."""
        self.calls.append(("upstream", request.url))
        if self.error is not None:
            raise self.error
        if self.result is None:
            raise AssertionError("RecordingUpstream needs a result or an error")
        return self.result


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
        self.release_count = 0

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
        """Record the settlement status and return a canned record."""
        self.calls.append(("settle", status))
        self.settle_statuses.append(status)
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
        self.release_count += 1
        self.calls.append(("release", reservation.request_id))


def make_service(
    calls: list[tuple[Any, ...]],
    *,
    channels: tuple[RelayChannel, ...] | None = None,
    model_suffix: dict[str, str] | None = None,
    converter: RecordingConverter | None = None,
    upstream: RecordingUpstream | None = None,
    authorizer: RecordingAuthorizer | None = None,
    billing: RecordingBilling | None = None,
) -> RelayGatewayService:
    """Assemble a service wired to recording doubles sharing *calls*."""
    config = RelayGatewayConfig(
        channels=channels if channels is not None else default_channels(),
        model_suffix=model_suffix or {},
    )
    return RelayGatewayService(
        converter=converter or RecordingConverter(calls),
        codec=RelayPayloadCodec(),
        registry=RecordingRegistry(config, calls),
        upstream=upstream or RecordingUpstream(calls),
        config=config,
        authorizer=authorizer,
        billing=billing,
    )


_UNSET = object()
_DEFAULT_SESSION = object()


def happy_service(
    calls: list[tuple[Any, ...]],
    *,
    channels: tuple[RelayChannel, ...] | None = None,
    target: RelayFormat = RelayFormat.CLAUDE,
    request_value: Any = None,
    upstream_payload: Any = _UNSET,
    losses: tuple[RelayLoss, ...] = (),
    warnings: tuple[str, ...] = (),
    with_authorizer: bool = True,
    with_billing: bool = True,
) -> RelayGatewayService:
    """Wire a service whose doubles all return success."""
    converter = RecordingConverter(
        calls,
        request_result=ok_request_result(
            request_value if request_value is not None else claude_request_dto(),
            target,
        ),
        response_result=ok_response_result(
            OpenAIChatResponse.from_dict({"id": "resp-1", "model": "m"}),
            target,
            losses=losses,
            warnings=warnings,
        ),
    )
    return make_service(
        calls=calls,
        channels=channels,
        converter=converter,
        upstream=RecordingUpstream(
            calls,
            result=ok_upstream(
                upstream_payload
                if upstream_payload is not _UNSET
                else claude_response_wire()
            ),
        ),
        authorizer=RecordingAuthorizer(calls) if with_authorizer else None,
        billing=RecordingBilling(calls) if with_billing else None,
    )


class TestRequestLifecycle:
    """Dependency call ordering and result assembly on the happy path."""

    @pytest.mark.asyncio
    async def test_successful_request_calls_dependencies_in_order(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = happy_service(
            calls,
            losses=(
                RelayLoss(
                    field="stream",
                    target=RelayFormat.CLAUDE,
                    reason="streaming_adapted",
                ),
            ),
            warnings=("warning-1",),
        )
        result = await service.handle(make_request())
        assert result.is_ok()
        gateway_result = result.unwrap()
        assert gateway_result.status_code == 200
        assert gateway_result.headers == {
            "content-type": "application/json",
            "x-request-id": REQUEST_ID,
        }
        assert gateway_result.payload == {
            "id": "resp-1",
            "object": "chat.completion",
            "created": 0,
            "model": "m",
            "choices": [],
        }
        assert gateway_result.stream is None
        metadata = gateway_result.metadata
        assert metadata is not None
        assert metadata.converter_id == "test_converter"
        assert metadata.source == SOURCE
        assert metadata.target == RelayFormat.CLAUDE
        assert metadata.quality == ConversionQuality.GOOD
        assert metadata.loss_codes == ("streaming_adapted",)
        assert metadata.warnings == ("warning-1",)
        assert calls == [
            ("authorize", TENANT_ID, "relay.invoke", MODEL),
            ("select", MODEL, False, None),
            ("pre_consume", TENANT_ID, "a"),
            ("convert_request", SOURCE, RelayFormat.CLAUDE),
            ("upstream", f"{BASE_URL}/v1/messages"),
            ("convert_response", RelayFormat.CLAUDE, SOURCE),
            ("settle", "completed"),
        ]

    @pytest.mark.asyncio
    async def test_no_authorizer_and_no_billing(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = happy_service(calls, with_authorizer=False, with_billing=False)
        result = await service.handle(make_request())
        assert result.is_ok()
        assert [call[0] for call in calls] == [
            "select",
            "convert_request",
            "upstream",
            "convert_response",
        ]

    @pytest.mark.asyncio
    async def test_model_suffix_applied(self) -> None:
        calls: list[tuple[Any, ...]] = []
        channels = (make_channel("a", target_format=RelayFormat.GEMINI),)
        service = make_service(
            calls=calls,
            channels=channels,
            model_suffix={"a": ":v1"},
            converter=RecordingConverter(
                calls,
                request_result=ok_request_result(
                    GeminiRequest.from_dict(
                        {"contents": [{"role": "user", "parts": [{"text": "hi"}]}]}
                    ),
                    RelayFormat.GEMINI,
                ),
                response_result=ok_response_result(
                    OpenAIChatResponse.from_dict({"id": "resp-1", "model": "m"}),
                    RelayFormat.GEMINI,
                ),
            ),
            upstream=RecordingUpstream(calls, result=ok_upstream({"candidates": []})),
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        result = await service.handle(make_request())
        assert result.is_ok()
        assert (
            "upstream",
            f"{BASE_URL}/v1beta/models/{MODEL}:v1:generateContent",
        ) in calls

    @pytest.mark.asyncio
    async def test_channel_preferred_hint_used(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = happy_service(calls)
        result = await service.handle(make_request(channel=make_channel("a")))
        assert result.is_ok()
        assert ("select", MODEL, False, "a") in calls


class TestShortCircuit:
    """Failures before the upstream call must short-circuit the pipeline."""

    @pytest.mark.asyncio
    async def test_authorize_failure_short_circuits(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls=calls,
            authorizer=RecordingAuthorizer(calls, allowed=False),
            billing=RecordingBilling(calls),
        )
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "AUTH_DENIED"
        assert err.status_code == 403
        assert err.request_id == REQUEST_ID
        assert [call[0] for call in calls] == ["authorize"]

    @pytest.mark.asyncio
    async def test_channel_selection_failure_short_circuits(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls=calls,
            channels=(make_channel("a", models=("other-model",)),),
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "MODEL_NOT_FOUND"
        assert err.status_code == 404
        assert err.request_id == REQUEST_ID
        assert [call[0] for call in calls] == ["authorize", "select"]

    @pytest.mark.asyncio
    async def test_request_conversion_failure_releases_reservation(self) -> None:
        calls: list[tuple[Any, ...]] = []
        converter = RecordingConverter(
            calls,
            request_result=Err(
                RelayError("malformed", RelayErrorCode.MALFORMED_PAYLOAD)
            ),
        )
        billing = RecordingBilling(calls)
        service = make_service(
            calls=calls,
            converter=converter,
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "INVALID_REQUEST"
        assert err.status_code == 400
        assert err.request_id == REQUEST_ID
        assert err.message == "malformed"
        assert "upstream" not in [call[0] for call in calls]
        assert billing.release_count == 1
        assert billing.settle_statuses == []


class TestUpstreamFailures:
    """Upstream and response decode failures map to safe gateway errors."""

    @pytest.mark.asyncio
    async def test_upstream_error_propagates_normalized(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream_error = RelayGatewayError(
            code="UPSTREAM_TIMEOUT",
            message="upstream request timed out",
            status_code=504,
            request_id="",
            retryable=True,
        )
        upstream = RecordingUpstream(calls, result=Err(upstream_error))
        billing = RecordingBilling(calls)
        service = make_service(
            calls=calls,
            upstream=upstream,
            converter=RecordingConverter(
                calls,
                request_result=ok_request_result(
                    claude_request_dto(), RelayFormat.CLAUDE
                ),
            ),
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "UPSTREAM_TIMEOUT"
        assert err.status_code == 504
        assert err.retryable is True
        assert err.request_id == REQUEST_ID
        assert "convert_response" not in [call[0] for call in calls]
        assert billing.settle_statuses == ["failed"]

    @pytest.mark.asyncio
    async def test_upstream_malformed_response_maps_to_502(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = happy_service(calls, upstream_payload=None)
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "UPSTREAM_MALFORMED"
        assert err.status_code == 502
        assert err.request_id == REQUEST_ID

    @pytest.mark.asyncio
    async def test_response_conversion_failure(self) -> None:
        calls: list[tuple[Any, ...]] = []
        converter = RecordingConverter(
            calls,
            request_result=ok_request_result(claude_request_dto(), RelayFormat.CLAUDE),
            response_result=Err(
                RelayError("unsupported", RelayErrorCode.UNSUPPORTED_FEATURE)
            ),
        )
        service = make_service(
            calls=calls,
            converter=converter,
            upstream=RecordingUpstream(
                calls,
                result=ok_upstream({"id": "msg-1", "model": "claude-x", "content": []}),
            ),
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "INVALID_REQUEST"
        assert err.status_code == 400
        assert err.request_id == REQUEST_ID
        assert [call[0] for call in calls][-2:] == ["convert_response", "settle"]

    @pytest.mark.asyncio
    async def test_unknown_exception_wrapped(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RecordingUpstream(calls, error=RuntimeError("boom"))
        service = make_service(
            calls=calls,
            upstream=upstream,
            converter=RecordingConverter(
                calls,
                request_result=ok_request_result(
                    claude_request_dto(), RelayFormat.CLAUDE
                ),
            ),
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "CONVERSION_FAILED"
        assert err.status_code == 500
        assert err.retryable is False
        assert err.request_id == REQUEST_ID
        assert err.message == "Unexpected relay gateway failure"
        assert "Traceback" not in str(err)


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


class RequestCapturingUpstream:
    """Upstream double that captures the resolved ``UpstreamRequest``."""

    def __init__(
        self,
        *,
        result: Result[UpstreamResponse, RelayGatewayError] | None = None,
    ) -> None:
        self.captured: UpstreamRequest | None = None
        self.result = result

    async def request(
        self, request: UpstreamRequest
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Record the request; return the canned result."""
        self.captured = request
        if self.result is not None:
            return self.result
        return ok_upstream(claude_response_wire())


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


class TestUpstreamChannelIdentity:
    """The selected channel's name travels on the upstream request."""

    @pytest.mark.asyncio
    async def test_normal_channel_name_propagates(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream()
        service = make_service(
            calls=calls,
            upstream=upstream,
            converter=RecordingConverter(
                calls,
                request_result=ok_request_result(
                    claude_request_dto(), RelayFormat.CLAUDE
                ),
                response_result=ok_response_result(
                    OpenAIChatResponse.from_dict({"id": "resp-1", "model": "m"}),
                    RelayFormat.CLAUDE,
                ),
            ),
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        result = await service.handle(make_request())
        assert result.is_ok()
        assert upstream.captured is not None
        assert upstream.captured.channel_name == "a"

    @pytest.mark.asyncio
    async def test_preferred_channel_name_propagates(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream()
        service = make_service(
            calls=calls,
            channels=(make_channel("a"), make_channel("b")),
            upstream=upstream,
            converter=RecordingConverter(
                calls,
                request_result=ok_request_result(
                    claude_request_dto(), RelayFormat.CLAUDE
                ),
                response_result=ok_response_result(
                    OpenAIChatResponse.from_dict({"id": "resp-1", "model": "m"}),
                    RelayFormat.CLAUDE,
                ),
            ),
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        result = await service.handle(make_request(channel=make_channel("b")))
        assert result.is_ok()
        assert upstream.captured is not None
        assert upstream.captured.channel_name == "b"


class StreamingUpstream:
    """Upstream double exposing the streaming surface the service drives.

    The gateway service type-annotates its upstream as
    ``HTTPUpstreamAdapter`` but only the ``stream`` and ``cancel``
    methods are used by the streaming branch, so this double satisfies
    the runtime surface.

    Attributes:
        calls: Recorded ``("stream", request_id)`` and ``("cancel",
            request_id)`` tuples.
        chunks: Upstream chunks replayed on every ``stream`` iteration.
    """

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        *,
        chunks: list[UpstreamChunk] | None = None,
    ) -> None:
        self.calls = calls
        self.chunks = list(chunks or [])

    async def stream(self, request: UpstreamRequest) -> Any:
        """Record the stream request and replay the scripted chunks."""
        self.calls.append(("stream", request.request_id))
        for chunk in self.chunks:
            yield chunk

    async def cancel(self, request_id: str) -> None:
        """Record the cancellation request."""
        self.calls.append(("cancel", request_id))

    async def request(self, request: UpstreamRequest) -> Any:
        """The buffered adapter path must never run in these tests."""
        raise AssertionError("buffered upstream.request called while streaming")


class StreamingConverter(RecordingConverter):
    """``RecordingConverter`` wired with a scripted stream session."""

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        *,
        request_result: Result[Any, RelayError] | None = None,
        session: StreamingSession | None = None,
    ) -> None:
        super().__init__(calls, request_result=request_result)
        self.session = session

    def new_stream_session(
        self,
        source: RelayFormat,
        target: RelayFormat,
        *,
        options: Any = None,
        context: Any = None,
        registry: Any = None,
    ) -> Result[Any, RelayError]:
        """Record the call and return the scripted session."""
        self.calls.append(("new_stream_session", source, target))
        if self.session is not None:
            return Ok(self.session)
        return Err(
            RelayError(
                code=RelayErrorCode.MALFORMED_PAYLOAD,
                message="no fake stream session configured",
            )
        )


class StreamingSessions:
    """Stateful stream session double replaying scripted wire events.

    Attributes:
        accepted: Source DTOs passed through ``accept``.
        finalized: Whether ``finalize`` already ran.
        usage: Optional snapshot usage mapping pass-through.
    """

    def __init__(self, *, usage: dict[str, int] | None = None) -> None:
        self.usage = usage
        self.accepted: list[object] = []
        self.finalized = False

    def accept(self, event: object) -> tuple[WireFrame, ...]:
        """Record the source DTO and emit one delta wire event."""
        self.accepted.append(event)
        return (WireFrame(type_="delta"),)

    def finalize(self) -> tuple[WireFrame, ...]:
        """Emit one terminal wire event exactly once."""
        if self.finalized:
            return ()
        self.finalized = True
        return (WireFrame(type_="final"),)

    def snapshot(self) -> dict[str, object]:
        """Return a usage-carrying snapshot when one is configured."""
        snapshot: dict[str, object] = {
            "accepted": len(self.accepted),
            "finalized": self.finalized,
        }
        if self.usage is not None:
            snapshot["usage"] = dict(self.usage)
        return snapshot


class WireFrame:
    """Minimal target wire event exposing ``type`` and ``to_dict``."""

    def __init__(self, type_: str) -> None:
        self.type = type_

    def to_dict(self) -> dict[str, str]:
        """The wire payload is the discriminant alone."""
        return {"type": self.type}


class RecordingStreams(RelayStreamRegistry):
    """Stream registry recording register/unregister and exposing handles.

    Attributes:
        calls: Recorded ``("register", channel, model)`` and
            ``("unregister", stream_id)`` tuples.
        last_stream_id: Identifier of the most recent registration;
            used to reach the cancel handle mid-stream.
    """

    def __init__(self, calls: list[tuple[Any, ...]]) -> None:
        super().__init__()
        self.calls = calls
        self.last_stream_id: str | None = None

    def register(
        self,
        *,
        channel: str,
        model: str,
        request_id: str,
    ) -> tuple[str, Any]:
        """Record the registration and remember the stream id."""
        self.calls.append(("register", channel, model))
        stream_id, handle = super().register(
            channel=channel, model=model, request_id=request_id
        )
        self.last_stream_id = stream_id
        return stream_id, handle

    def unregister(self, stream_id: str) -> None:
        """Record the deregistration."""
        self.calls.append(("unregister", stream_id))
        return super().unregister(stream_id)


class SettleCapturingBilling(RecordingBilling):
    """RecordingBilling that also keeps every settled result."""

    def __init__(self, calls: list[tuple[Any, ...]]) -> None:
        super().__init__(calls)
        self.settled_results: list[Any] = []

    async def settle(
        self,
        reservation: RelayUsageReservation,
        result: Any,
        *,
        status: str,
    ) -> Any:
        """Record the settled result with the status."""
        self.settled_results.append(result)
        return await super().settle(reservation, result, status=status)


def _claude_stream_chunks(*, terminal: bool = True) -> list[UpstreamChunk]:
    """Claude-style SSE chunks, optionally ending in ``message_stop``."""
    frames = [
        UpstreamChunk(
            event=None,
            data='{"type": "content_block_delta", "index": 0, '
            '"delta": {"type": "text_delta", "text": "hi"}}',
        ),
        UpstreamChunk(
            event=None,
            data='{"type": "content_block_delta", "index": 0, '
            '"delta": {"type": "text_delta", "text": " there"}}',
        ),
    ]
    if terminal:
        frames.append(UpstreamChunk(event=None, data='{"type": "message_stop"}'))
    return frames


def streaming_service(
    calls: list[tuple[Any, ...]],
    *,
    chunks: list[UpstreamChunk] | None = None,
    session: StreamingSessions | None | object = _DEFAULT_SESSION,
    billing: RecordingBilling | None = None,
    streams: RecordingStreams | None = None,
    authorizer: RecordingAuthorizer | None = None,
) -> RelayGatewayService:
    """Assemble a streaming-capable service over scripted doubles.

    Args:
        calls: Shared recording list.
        chunks: Upstream chunks; defaults to a terminal Claude stream.
        session: Stream session factory result; ``None`` makes the
            session factory fail (preflight error path).
        billing: Billing double; ``None`` disables billing.
        streams: Stream registry double; ``None`` disables registration.
        authorizer: Authorizer double; ``None`` skips authorization.
    """
    converter = StreamingConverter(
        calls,
        request_result=ok_request_result(
            claude_request_dto(),
            RelayFormat.CLAUDE,
        ),
        session=(
            StreamingSessions()
            if session is _DEFAULT_SESSION
            else session
        ),
    )
    config = RelayGatewayConfig(channels=default_channels())
    return RelayGatewayService(
        converter=converter,
        codec=RelayPayloadCodec(),
        registry=RecordingRegistry(config, calls),
        upstream=StreamingUpstream(  # type: ignore[arg-type]
            calls,
            chunks=chunks or _claude_stream_chunks(),
        ),
        config=config,
        authorizer=authorizer,
        billing=billing,
        streams=streams,
    )


class TestLoadBalancingConfig:
    """load_balancing mode on RelayGatewayConfig (plan H, task 1)."""

    def test_defaults_to_deterministic(self) -> None:
        config = RelayGatewayConfig()
        assert config.load_balancing == "deterministic"

    def test_accepts_weighted(self) -> None:
        config = RelayGatewayConfig(load_balancing="weighted")
        assert config.load_balancing == "weighted"

    def test_rejects_unknown_mode(self) -> None:
        with pytest.raises(ValueError):
            RelayGatewayConfig(load_balancing="random")  # type: ignore[arg-type]


class TestStreamingService:
    """Streaming request lifecycle of ``RelayGatewayService``."""

    @pytest.mark.asyncio
    async def test_stream_request_preflight_returns_lazy_stream(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = streaming_service(calls, billing=billing, streams=RecordingStreams(calls))
        result = await service.handle(make_request(stream=True))
        assert result.is_ok()
        outcome = result.unwrap()
        assert outcome.status_code == 200
        assert outcome.payload is None
        assert outcome.stream is not None
        assert ("select", MODEL, True, None) in calls
        assert ("stream", REQUEST_ID) not in calls
        assert billing.settle_statuses == []

    @pytest.mark.asyncio
    async def test_stream_consumes_events_and_settles_completed(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = SettleCapturingBilling(calls)
        session = StreamingSessions(usage={"prompt_tokens": 7, "completion_tokens": 4})
        service = streaming_service(
            calls, billing=billing, session=session, streams=RecordingStreams(calls)
        )
        result = await service.handle(make_request(stream=True))
        events = [event async for event in result.unwrap().stream or ()]
        assert [event.event for event in events] == ["delta", "delta", "final"]
        assert billing.settle_statuses == ["completed"]
        assert billing.settled_results[0].usage is not None
        assert billing.settled_results[0].usage.prompt_tokens == 7
        assert billing.settled_results[0].usage.completion_tokens == 4
        assert ("cancel", REQUEST_ID) not in calls

    @pytest.mark.asyncio
    async def test_stream_without_terminal_marker_settles_truncated(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = streaming_service(
            calls,
            chunks=_claude_stream_chunks(terminal=False),
            billing=billing,
        )
        result = await service.handle(make_request(stream=True))
        events = [event async for event in (result.unwrap().stream or ())]
        assert events
        assert billing.settle_statuses == ["truncated"]

    @pytest.mark.asyncio
    async def test_consumer_disconnect_cancels_and_settles_cancelled(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = streaming_service(
            calls, billing=billing, streams=RecordingStreams(calls)
        )
        result = await service.handle(make_request(stream=True))
        iterator = (result.unwrap().stream or ()).__aiter__()
        await iterator.__anext__()
        await iterator.aclose()
        assert ("cancel", REQUEST_ID) in calls
        assert billing.settle_statuses == ["cancelled"]

    @pytest.mark.asyncio
    async def test_malformed_chunk_raises_and_settles_truncated(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = streaming_service(
            calls,
            chunks=[UpstreamChunk(event=None, data="not-json")],
            billing=billing,
            streams=RecordingStreams(calls),
        )
        result = await service.handle(make_request(stream=True))
        with pytest.raises(RelayGatewayError):
            await result.unwrap().stream.__anext__()
        assert ("cancel", REQUEST_ID) in calls
        assert billing.settle_statuses == ["truncated"]

    @pytest.mark.asyncio
    async def test_operator_cancel_stops_stream_and_settles_cancelled(self) -> None:
        calls: list[tuple[Any, ...]] = []
        streams = RecordingStreams(calls)
        service = streaming_service(calls, billing=RecordingBilling(calls), streams=streams)
        result = await service.handle(make_request(stream=True))
        iterator = (result.unwrap().stream or ()).__aiter__()
        await iterator.__anext__()
        assert streams.last_stream_id is not None
        handle = streams.handle(streams.last_stream_id)
        assert handle is not None
        handle.set()
        with pytest.raises(StopAsyncIteration):
            await iterator.__anext__()
        assert calls.count(("cancel", REQUEST_ID)) == 1

    @pytest.mark.asyncio
    async def test_stream_without_registry_still_consumes_and_settles(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = streaming_service(calls, billing=billing)
        result = await service.handle(make_request(stream=True))
        events = [event async for event in (result.unwrap().stream or ())]
        assert events
        assert billing.settle_statuses == ["completed"]

    @pytest.mark.asyncio
    async def test_stream_preflight_session_error_short_circuits(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = streaming_service(
            calls,
            session=None,
            billing=billing,
        )
        result = await service.handle(make_request(stream=True))
        assert result.is_err()
        assert billing.settle_statuses == []
        assert billing.release_count == 1

    @pytest.mark.asyncio
    async def test_stream_auth_denial_short_circuits(self) -> None:
        calls: list[tuple[Any, ...]] = []
        authorizer = RecordingAuthorizer(calls, allowed=False)
        service = streaming_service(calls, authorizer=authorizer)
        result = await service.handle(make_request(stream=True))
        assert result.is_err()
        assert result.unwrap_err().code == "AUTH_DENIED"
        assert not [call for call in calls if call[0] == "stream"]

    @pytest.mark.asyncio
    async def test_stream_registered_and_unregistered(self) -> None:
        calls: list[tuple[Any, ...]] = []
        streams = RecordingStreams(calls)
        service = streaming_service(calls, streams=streams)
        result = await service.handle(make_request(stream=True))
        events = [event async for event in (result.unwrap().stream or ())]
        assert events
        register = [call for call in calls if call[0] == "register"]
        unregister = [call for call in calls if call[0] == "unregister"]
        assert len(register) == 1
        assert register[0][1] == "a"
        assert register[0][2] == MODEL
        assert len(unregister) == 1
        assert streams.list() == ()
