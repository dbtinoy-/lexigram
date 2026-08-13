"""Relay gateway service lifecycle tests (Relay Gateway plan, Task 4).

Verifies the buffered request pipeline: dependency call ordering,
short-circuit behavior on authorize/channel/conversion failures,
upstream error normalization, preferred-channel hints, model suffixes,
and result metadata assembly of ``RelayGatewayService``.

Auth, billing, and streaming behavior live in ``test_service_auth.py``,
``test_service_billing.py``, and ``test_service_streaming.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.contracts.ai.exceptions import RelayError, RelayErrorCode
from lexigram.contracts.ai.relay import (
    ConversionQuality,
    GeminiRequest,
    RelayFormat,
    RelayGatewayError,
    RelayLoss,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.ai.relay.dto import OpenAIChatResponse
from lexigram.contracts.core.result import Err, Result
from service_test_helpers import (
    MODEL,
    REQUEST_ID,
    SOURCE,
    TENANT_ID,
    RecordingAuthorizer,
    RecordingBilling,
    RecordingConverter,
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

BASE_URL = "https://upstream.example.com"


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


class TestLoadBalancingConfig:
    """load_balancing mode on RelayGatewayConfig (plan H, task 1)."""

    def test_defaults_to_deterministic(self) -> None:
        config = RelayGatewayConfig()
        assert config.load_balancing == "deterministic"

    def test_accepts_weighted(self) -> None:
        config = RelayGatewayConfig(load_balancing="weighted")
        assert config.load_balancing == "weighted"

    def test_rejects_unknown_mode(self) -> None:
        with pytest.raises(ValueError, match="load_balancing must be"):
            RelayGatewayConfig(load_balancing="random")  # type: ignore[arg-type]
