"""Relay gateway failover and outbound-model mapping tests.

Covers the channel ``model_map`` through the buffered dispatch path
(``operations.upstream.outbound_model``), upstream failure/success
accounting against a real ``RelayFailoverTracker``, and the
tracked-error-code boundary.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.operations import upstream
from lexigram.ai.relay.gateway.operations.failover import RelayFailoverTracker
from lexigram.ai.relay.gateway.service import RelayGatewayService
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay import (
    ClaudeRequest,
    ConversionQuality,
    OpenAIChatRequest,
    RelayChannel,
    RelayConvertResult,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.core.result import Err, Ok, Result

SOURCE = RelayFormat.OPENAI_CHAT
MODEL = "test-model"
BASE_URL = "https://upstream.example.com"


def make_channel(name: str = "a", **overrides: Any) -> RelayChannel:
    """Build an enabled CLAUDE channel; ``overrides`` win."""
    defaults: dict[str, Any] = {
        "name": name,
        "upstream_base_url": BASE_URL,
        "target_format": RelayFormat.CLAUDE,
        "models": (MODEL,),
    }
    defaults.update(overrides)
    return RelayChannel(**defaults)


def make_request(model: str = MODEL) -> RelayGatewayRequest:
    """A minimal OpenAI Chat relay request."""
    return RelayGatewayRequest(
        request_id="req-1",
        tenant_id="tenant-1",
        source=SOURCE,
        model=model,
        stream=False,
        payload=OpenAIChatRequest.from_dict({"model": model}).to_dict(),
        headers={},
    )


def ok_converted(value: Any, target: RelayFormat) -> Result[Any, RelayError]:
    """A canned Ok ``convert_request`` result in the CLAUDE family."""
    return Ok(
        RelayConvertResult(
            value=value,
            source=SOURCE,
            target=target,
            converter_id="test_converter",
            quality=ConversionQuality.GOOD,
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
    """A minimal valid Claude request DTO."""
    return ClaudeRequest.from_dict(
        {"model": "claude-x", "max_tokens": 1024, "messages": []}
    )


def claude_response_wire() -> dict[str, Any]:
    """A minimal valid Claude response wire dict."""
    return {
        "id": "msg-1",
        "model": "claude-x",
        "content": [{"type": "text", "text": "hi"}],
    }


class RecordingUpstream:
    """Upstream double recording which channel it was invoked for."""

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        *,
        result: Result[UpstreamResponse, RelayGatewayError],
    ) -> None:
        self.calls = calls
        self.result = result

    async def request(
        self, request: UpstreamRequest
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Record the channel name and return the canned result."""
        self.calls.append(
            ("upstream", request.channel_name, request.payload.get("model"))
        )
        return self.result


class RecordingConverter:
    """Converter double returning canned request/response conversions."""

    def __init__(self, calls: list[tuple[Any, ...]]) -> None:
        self.calls = calls
        self.converted_model: str | None = None

    def convert_request(
        self,
        payload: Any,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: Any = None,
        registry: Any = None,
    ) -> Result[Any, RelayError]:
        """Record the call; stash the outbound model for later assertion."""
        self.calls.append(("convert_request", source, target))
        self.converted_model = context.upstream_model if context is not None else None
        return ok_converted(claude_request_dto(), target)

    def convert_response(
        self,
        payload: Any,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: Any = None,
        registry: Any = None,
    ) -> Result[Any, RelayError]:
        """Record the call and return the canned success."""
        self.calls.append(("convert_response", source, target))
        return Ok(
            RelayConvertResult(
                value=OpenAIChatRequest.from_dict({"model": MODEL}),
                source=source,
                target=target,
                converter_id="test_converter",
                quality=ConversionQuality.GOOD,
            )
        )


def service(
    converter: RecordingConverter,
    upstream: RecordingUpstream,
    channels: tuple[RelayChannel, ...],
    *,
    model_suffix: dict[str, str] | None = None,
    failover: RelayFailoverTracker | None = None,
) -> RelayGatewayService:
    """Assemble a gateway service over the given parts."""
    config = RelayGatewayConfig(
        channels=channels,
        model_suffix=model_suffix or {},
        max_upstream_retries=0,
    )
    return RelayGatewayService(
        converter=converter,
        codec=RelayPayloadCodec(),
        registry=RelayChannelRegistry(config),
        upstream=upstream,
        config=config,
        failover=failover,
    )


class TestOutboundModelMapping:
    """The buffered dispatch path applies ``model_map`` then the suffix."""

    @pytest.mark.asyncio
    async def test_model_map_rewrites_upstream_model(self) -> None:
        calls: list[tuple[Any, ...]] = []
        converter = RecordingConverter(calls)
        channels = (
            make_channel(
                "a",
                models=("test-model", "alias"),
                model_map={"alias": "claude-sonnet"},
            ),
        )
        svc = service(
            converter,
            RecordingUpstream(calls, result=ok_upstream(claude_response_wire())),
            channels,
        )
        result = await svc.handle(make_request(model="alias"))
        assert result.is_ok()
        assert converter.converted_model == "claude-sonnet"

    @pytest.mark.asyncio
    async def test_model_map_then_suffix_applied(self) -> None:
        calls: list[tuple[Any, ...]] = []
        converter = RecordingConverter(calls)
        channels = (
            make_channel(
                "a",
                models=("test-model", "alias"),
                model_map={"alias": "claude-sonnet"},
            ),
        )
        svc = service(
            converter,
            RecordingUpstream(calls, result=ok_upstream(claude_response_wire())),
            channels,
            model_suffix={"a": ":thinking"},
        )
        result = await svc.handle(make_request(model="alias"))
        assert result.is_ok()
        assert converter.converted_model == "claude-sonnet:thinking"

    @pytest.mark.asyncio
    async def test_unmapped_alias_passes_through(self) -> None:
        calls: list[tuple[Any, ...]] = []
        converter = RecordingConverter(calls)
        svc = service(
            converter,
            RecordingUpstream(calls, result=ok_upstream(claude_response_wire())),
            (make_channel("a"),),
        )
        result = await svc.handle(make_request())
        assert result.is_ok()
        assert converter.converted_model == MODEL


class TestFailoverAccounting:
    """Upstream failures and successes count against the tracker."""

    @pytest.mark.asyncio
    async def test_upstream_failure_counts_and_bans_channel(self) -> None:
        calls: list[tuple[Any, ...]] = []
        channels = (
            make_channel("a", models=(MODEL,)),
            make_channel("b", models=(MODEL,)),
        )
        registry = RelayChannelRegistry(RelayGatewayConfig(channels=channels))
        tracker = RelayFailoverTracker(registry=registry, threshold=1)
        converter = RecordingConverter(calls)
        err = RelayGatewayError(
            code="UPSTREAM_FAILED",
            message="upstream unavailable",
            status_code=502,
            request_id="",
        )
        svc = service(
            converter,
            RecordingUpstream(calls, result=Err(err)),
            channels,
            failover=tracker,
        )
        result = await svc.handle(make_request())
        assert result.is_err()
        assert "a" in tracker.banned()
        assert registry.runtime_enabled() == {"a": False}

    @pytest.mark.asyncio
    async def test_success_resets_failures_and_restores_channel(self) -> None:
        calls: list[tuple[Any, ...]] = []
        channels = (
            make_channel("a", models=(MODEL,)),
            make_channel("b", models=(MODEL,)),
        )
        registry = RelayChannelRegistry(RelayGatewayConfig(channels=channels))
        tracker = RelayFailoverTracker(registry=registry, threshold=1)
        tracker.record_failure("a")
        assert "a" in tracker.banned()
        converter = RecordingConverter(calls)
        svc = service(
            converter,
            RecordingUpstream(calls, result=ok_upstream(claude_response_wire())),
            channels,
            failover=tracker,
        )
        result = await svc.handle(make_request())
        assert result.is_ok()
        assert "a" not in tracker.banned()
        assert tracker.failure_count("a") == 0

    @pytest.mark.asyncio
    async def test_no_tracker_means_no_accounting(self) -> None:
        calls: list[tuple[Any, ...]] = []
        err = RelayGatewayError(
            code="UPSTREAM_FAILED",
            message="upstream unavailable",
            status_code=502,
            request_id="",
        )
        svc = service(
            RecordingConverter(calls),
            RecordingUpstream(calls, result=Err(err)),
            (make_channel("a"),),
        )
        result = await svc.handle(make_request())
        assert result.is_err()
        assert svc._failover is None


class TestTrackedErrorCodes:
    """Only transport-level upstream failures count toward a ban."""

    def test_transport_failures_are_tracked(self) -> None:
        for code in ("UPSTREAM_ERROR", "UPSTREAM_TIMEOUT", "UPSTREAM_FAILED"):
            assert upstream.should_track_upstream_failure(code)

    def test_client_side_failures_are_not_tracked(self) -> None:
        for code in ("CLIENT_CANCELLED", "CLIENT_TRUNCATED", "INVALID_REQUEST"):
            assert not upstream.should_track_upstream_failure(code)
