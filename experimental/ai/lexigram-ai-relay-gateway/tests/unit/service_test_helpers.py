"""Shared doubles and builders for ``RelayGatewayService`` unit tests.

Extracted from ``test_service.py`` so split test modules (auth, billing,
streaming, validation) reuse the same scripted doubles without
duplication.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.service import RelayGatewayService
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.governance import (
    RelayBillingError,
    RelayUsageRecord,
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    ClaudeRequest,
    ConversionQuality,
    OpenAIChatRequest,
    RelayChannel,
    RelayConvertResult,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayLoss,
    RelayUsage,
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
    *,
    request_id: str = REQUEST_ID,
    tenant_id: str = TENANT_ID,
) -> RelayGatewayRequest:
    """Build a ``RelayGatewayRequest`` with an OpenAI Chat wire payload."""
    return RelayGatewayRequest(
        request_id=request_id,
        tenant_id=tenant_id,
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
        *,
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
