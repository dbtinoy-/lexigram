"""Passthrough service tests (Relay Gateway Plan J, Task 2).

Verifies the no-conversion lifecycle of ``PassthroughService``: channel
selection by endpoint kind, verbatim body forwarding with model-suffix
substitution, authorization/billing hook ordering, and error
classification — all mirroring the buffered chat pipeline without
``RelayConverterProtocol`` involvement.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.passthrough import (
    PassthroughService,
    RelayPassthroughBody,
    RelayPassthroughResult,
    rewrite_multipart_form_field,
)
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

KIND = "embeddings"
MODEL = "text-embedding-3-small"
REQUEST_ID = "req-123"
TENANT_ID = "tenant-1"
BASE_URL = "https://upstream.example.com"
WHITESPACE_BODY = {"model": MODEL, "input": ["hello"], "encoding_format": "float"}

MULTIPART_BOUNDARY = "bnd-42"
MULTIPART_CONTENT_TYPE = f"multipart/form-data; boundary={MULTIPART_BOUNDARY}"
MULTIPART_BODY = b"".join(
    [
        f"--{MULTIPART_BOUNDARY}\r\n".encode("ascii"),
        b'Content-Disposition: form-data; name="model"\r\n',
        b"\r\n",
        MODEL.encode("ascii"),
        b"\r\n",
        f"--{MULTIPART_BOUNDARY}\r\n".encode("ascii"),
        b'Content-Disposition: form-data; name="image"; filename="starry.png"\r\n',
        b"Content-Type: image/png\r\n",
        b"\r\n",
        b"\x89PNG\r\n\x1a\nBINARY\x00\xffDATA",
        b"\r\n",
        f"--{MULTIPART_BOUNDARY}--\r\n".encode("ascii"),
    ]
)
"""A two-part multipart body: a ``model`` field plus a binary ``image`` part."""


def make_channel(name: str = "a", **overrides: Any) -> RelayChannel:
    """Build an embeddings-capable channel with defaults; ``overrides`` win."""
    defaults: dict[str, Any] = {
        "name": name,
        "upstream_base_url": BASE_URL,
        "target_format": RelayFormat.OPENAI_CHAT,
        "models": (MODEL,),
        "endpoint_kinds": frozenset({"embeddings"}),
    }
    defaults.update(overrides)
    return RelayChannel(**defaults)


def default_channels() -> tuple[RelayChannel, ...]:
    """One enabled embeddings channel plus one disabled channel."""
    return (make_channel("a"), make_channel("b", enabled=False))


def make_request(
    model: str = MODEL,
    payload: RelayPassthroughBody | dict[str, Any] | None = None,
    channel: RelayChannel | None = None,
) -> RelayGatewayRequest:
    """Build a passthrough ``RelayGatewayRequest`` with an embeddings body."""
    return RelayGatewayRequest(
        request_id=REQUEST_ID,
        tenant_id=TENANT_ID,
        source=RelayFormat.OPENAI_CHAT,
        model=model,
        stream=False,
        payload=payload if payload is not None else dict(WHITESPACE_BODY),
        headers={},
        channel=channel,
    )


def ok_binary_upstream(
    body: bytes,
    content_type: str,
    status_code: int = 200,
) -> Result[UpstreamResponse, RelayGatewayError]:
    """A canned Ok binary upstream result."""
    return Ok(
        UpstreamResponse(
            status_code=status_code,
            headers={"content-type": content_type},
            payload=body,
        )
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
        self.settle_usages: list[RelayUsage | None] = []
        self.settled_usages: list[RelayUsage | None] = []

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


def default_upstream_response() -> dict[str, Any]:
    """A canned OpenAI-shaped embeddings response body."""
    return {
        "object": "list",
        "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}],
        "model": MODEL,
        "usage": {"prompt_tokens": 5, "total_tokens": 5},
    }


def make_service(
    calls: list[tuple[Any, ...]],
    *,
    channels: tuple[RelayChannel, ...] | None = None,
    model_suffix: dict[str, str] | None = None,
    upstream: RecordingUpstream | None = None,
    authorizer: RecordingAuthorizer | None = None,
    billing: RecordingBilling | None = None,
) -> PassthroughService:
    """Assemble a passthrough service wired to recording doubles."""
    config = RelayGatewayConfig(
        channels=channels if channels is not None else default_channels(),
        model_suffix=model_suffix or {},
    )
    return PassthroughService(
        registry=RecordingRegistry(config, calls),
        upstream=upstream
        or RecordingUpstream(calls, result=ok_upstream(default_upstream_response())),
        config=config,
        authorizer=authorizer,
        billing=billing,
    )


class RequestCapturingUpstream:
    """Upstream double that captures the resolved ``UpstreamRequest``."""

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        *,
        result: Result[UpstreamResponse, RelayGatewayError] | None = None,
    ) -> None:
        self.calls = calls
        self.captured: UpstreamRequest | None = None
        self.result = result

    async def request(
        self, request: UpstreamRequest
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Record the request; return the canned result."""
        self.calls.append(("upstream", request.url))
        self.captured = request
        if self.result is not None:
            return self.result
        return ok_upstream(
            {
                "object": "list",
                "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}],
                "model": MODEL,
                "usage": {"prompt_tokens": 5, "total_tokens": 5},
            }
        )


class TestRequestLifecycle:
    """Happy-path forwarding: ordering, suffix substitution, verbatim body."""

    @pytest.mark.asyncio
    async def test_successful_request_forwards_verbatim_with_order(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(calls)
        body = {"model": MODEL, "input": ["hello"], "dimensions": 128}
        service = make_service(
            calls=calls,
            upstream=upstream,
            model_suffix={"a": ":legacy"},
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        result = await service.handle("embeddings", make_request(payload=body))
        assert result.is_ok()
        gateway_result = result.unwrap()
        assert gateway_result.status_code == 200
        assert gateway_result.headers == {
            "content-type": "application/json",
            "x-request-id": REQUEST_ID,
        }
        assert gateway_result.payload == {
            "object": "list",
            "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}],
            "model": MODEL,
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }
        assert gateway_result.stream is None
        assert gateway_result.metadata is None
        assert calls == [
            ("authorize", TENANT_ID, "relay.invoke", MODEL),
            ("select_endpoint", "embeddings", MODEL),
            ("pre_consume", TENANT_ID, "a"),
            ("upstream", f"{BASE_URL}/v1/embeddings"),
            ("settle", "completed"),
        ]
        assert upstream.captured is not None
        assert upstream.captured.url == f"{BASE_URL}/v1/embeddings"
        assert upstream.captured.method == "POST"
        assert upstream.captured.channel_name == "a"
        assert upstream.captured.payload == {
            "model": f"{MODEL}:legacy",
            "input": ["hello"],
            "dimensions": 128,
        }

    @pytest.mark.asyncio
    async def test_no_authorizer_no_billing_runs_select_and_call(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(calls, authorizer=None, billing=None)
        result = await service.handle("embeddings", make_request())
        assert result.is_ok()
        assert [call[0] for call in calls] == ["select_endpoint", "upstream"]

    @pytest.mark.asyncio
    async def test_body_verbatim_except_model_substitution(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(calls)
        body = {
            "model": MODEL,
            "input": [["a", "b"], "c"],
            "encoding_format": "float",
            "extra_field": {"nested": True},
        }
        service = make_service(calls, upstream=upstream)
        result = await service.handle("embeddings", make_request(payload=body))
        assert result.is_ok()
        assert upstream.captured is not None
        assert upstream.captured.payload == {
            "model": MODEL,
            "input": [["a", "b"], "c"],
            "encoding_format": "float",
            "extra_field": {"nested": True},
        }

    @pytest.mark.asyncio
    async def test_original_payload_not_mutated(self) -> None:
        calls: list[tuple[Any, ...]] = []
        body = {**WHITESPACE_BODY, "input": ["x"]}
        service = make_service(calls, model_suffix={"a": ":v2"})
        result = await service.handle("embeddings", make_request(payload=body))
        assert result.is_ok()
        assert body == {**WHITESPACE_BODY, "input": ["x"]}


class TestSelectionFailures:
    """Endpoint-kind selection failures map to the chat error family."""

    @pytest.mark.asyncio
    async def test_no_channel_declares_kind_is_model_not_found(self) -> None:
        calls: list[tuple[Any, ...]] = []
        chat_only = (make_channel("chat", endpoint_kinds=frozenset()),)
        service = make_service(calls, channels=chat_only)
        result = await service.handle("embeddings", make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "MODEL_NOT_FOUND"
        assert err.status_code == 404
        assert err.request_id == REQUEST_ID

    @pytest.mark.asyncio
    async def test_kind_channel_missing_model_is_model_not_found(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls, channels=(make_channel("a", models=("other-model",)),)
        )
        result = await service.handle("embeddings", make_request())
        assert result.is_err()
        assert result.unwrap_err().code == "MODEL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_all_channels_disabled_is_channel_disabled(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(calls, channels=(make_channel("a", enabled=False),))
        result = await service.handle("embeddings", make_request())
        assert result.is_err()
        assert result.unwrap_err().code == "CHANNEL_DISABLED"

    @pytest.mark.asyncio
    async def test_unknown_endpoint_kind_is_invalid_request(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(calls)
        result = await service.handle("images", make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "INVALID_REQUEST"
        assert err.status_code == 400
        assert err.request_id == REQUEST_ID
        assert [call[0] for call in calls] == []


class TestShortCircuits:
    """Authorization and billing failures fail before the upstream call."""

    @pytest.mark.asyncio
    async def test_authorize_failure_short_circuits(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls,
            authorizer=RecordingAuthorizer(calls, allowed=False),
            billing=RecordingBilling(calls),
        )
        result = await service.handle("embeddings", make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "AUTH_DENIED"
        assert err.status_code == 403
        assert err.request_id == REQUEST_ID
        assert [call[0] for call in calls] == ["authorize"]

    @pytest.mark.asyncio
    async def test_billing_denial_fails_before_upstream(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls, admit=False)
        service = make_service(
            calls,
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.handle("embeddings", make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "QUOTA_EXCEEDED"
        assert err.status_code == 429
        assert err.retryable is True
        assert err.request_id == REQUEST_ID
        assert [call[0] for call in calls] == [
            "authorize",
            "select_endpoint",
            "pre_consume",
        ]


class TestUpstreamFailures:
    """Upstream failures settle as failed and map to safe errors."""

    @pytest.mark.asyncio
    async def test_upstream_error_settles_failed_and_propagates(self) -> None:
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
            upstream=RecordingUpstream(calls, result=Err(upstream_error)),
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.handle("embeddings", make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "UPSTREAM_TIMEOUT"
        assert err.status_code == 504
        assert err.retryable is True
        assert err.request_id == REQUEST_ID
        assert billing.settle_statuses == ["failed"]

    @pytest.mark.asyncio
    async def test_malformed_upstream_body_maps_to_502(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls,
            upstream=RecordingUpstream(calls, result=ok_upstream(None)),
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        result = await service.handle("embeddings", make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "UPSTREAM_MALFORMED"
        assert err.status_code == 502
        assert err.request_id == REQUEST_ID

    @pytest.mark.asyncio
    async def test_unknown_exception_wrapped_safe(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls,
            upstream=RecordingUpstream(calls, error=RuntimeError("boom")),
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        result = await service.handle("embeddings", make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "CONVERSION_FAILED"
        assert err.status_code == 500
        assert err.retryable is False
        assert err.request_id == REQUEST_ID


class TestBillingUsage:
    """Settlement carries the upstream-reported usage when present."""

    @pytest.mark.asyncio
    async def test_settle_completed_with_extracted_usage(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = make_service(
            calls,
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.handle("embeddings", make_request())
        assert result.is_ok()
        assert billing.settle_statuses == ["completed"]
        assert billing.settle_usages == [RelayUsage(prompt_tokens=5)]

    @pytest.mark.asyncio
    async def test_settle_usage_missing_when_upstream_omits_it(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = make_service(
            calls,
            upstream=RecordingUpstream(
                calls, result=ok_upstream({"object": "list", "data": []})
            ),
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.handle("embeddings", make_request())
        assert result.is_ok()
        assert billing.settle_usages == [None]

    @pytest.mark.asyncio
    async def test_settle_failure_never_fails_the_response(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = FailingSettling(calls)
        service = make_service(
            calls,
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.handle("embeddings", make_request())
        assert result.is_ok()


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


class TestRelayPassthroughBody:
    """``RelayPassthroughBody`` construction and value semantics (Plan K, Task 0)."""

    def test_json_wraps_dict_as_json_content_type(self) -> None:
        body = RelayPassthroughBody.json(dict(WHITESPACE_BODY))
        assert body.data == WHITESPACE_BODY
        assert body.content_type == "application/json"
        assert isinstance(body.data, dict)
        assert dict(body) == WHITESPACE_BODY
        assert body["model"] == MODEL
        assert "model" in body
        assert list(body) == list(WHITESPACE_BODY)
        assert len(body) == len(WHITESPACE_BODY)

    def test_json_wraps_without_mutating_source(self) -> None:
        source = dict(WHITESPACE_BODY)
        body = RelayPassthroughBody.json(source)
        source["model"] = "mutated"
        assert body["model"] == MODEL

    def test_raw_keeps_bytes_and_content_type(self) -> None:
        body = RelayPassthroughBody.raw(MULTIPART_BODY, MULTIPART_CONTENT_TYPE)
        assert body.data == MULTIPART_BODY
        assert body.content_type == MULTIPART_CONTENT_TYPE

    def test_raw_body_is_not_a_json_mapping(self) -> None:
        body = RelayPassthroughBody.raw(b"bytes", "application/octet-stream")
        with pytest.raises(TypeError):
            dict(body)
        with pytest.raises(TypeError):
            body["model"]

    def test_json_and_raw_of_same_bytes_are_distinct(self) -> None:
        raw = RelayPassthroughBody.raw(MULTIPART_BODY, MULTIPART_CONTENT_TYPE)
        assert raw != RelayPassthroughBody.json({"model": MODEL})

    def test_result_carries_body_content_type_status(self) -> None:
        result = RelayPassthroughResult(
            body=b"\x00\xff", content_type="audio/mpeg", status_code=200
        )
        assert result.body == b"\x00\xff"
        assert result.content_type == "audio/mpeg"
        assert result.status_code == 200
        assert result.payload is None
        assert result.headers == {}


class TestBinaryResponsePassthrough:
    """Non-JSON upstream responses return verbatim (Plan K, Task 1)."""

    @pytest.mark.asyncio
    async def test_json_response_roundtrip_is_unchanged(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(calls)
        service = make_service(calls, upstream=upstream)
        result = await service.handle("embeddings", make_request())
        assert result.is_ok()
        gateway_result = result.unwrap()
        assert gateway_result.content_type == "application/json"
        assert gateway_result.payload == default_upstream_response()
        assert upstream.captured is not None
        assert upstream.captured.headers == {"content-type": "application/json"}

    @pytest.mark.asyncio
    async def test_raw_audio_response_returned_verbatim(self) -> None:
        calls: list[tuple[Any, ...]] = []
        audio = b"\x00\xff\xfeMP3BINARYDATA"
        service = make_service(
            calls,
            upstream=RecordingUpstream(
                calls, result=ok_binary_upstream(audio, "audio/mpeg")
            ),
        )
        result = await service.handle("embeddings", make_request())
        assert result.is_ok()
        gateway_result = result.unwrap()
        assert gateway_result.status_code == 200
        assert gateway_result.body == audio
        assert gateway_result.content_type == "audio/mpeg"
        assert gateway_result.payload is None
        assert gateway_result.headers == {
            "content-type": "audio/mpeg",
            "x-request-id": REQUEST_ID,
        }

    @pytest.mark.asyncio
    async def test_non_json_response_is_not_an_error(self) -> None:
        calls: list[tuple[Any, ...]] = []
        raw = b"\x1f\x8b\x08binary-blob"
        result = await make_service(
            calls,
            upstream=RecordingUpstream(
                calls, result=ok_binary_upstream(raw, "application/octet-stream")
            ),
        ).handle("embeddings", make_request())
        assert result.is_ok()
        assert result.unwrap().body == raw

    @pytest.mark.asyncio
    async def test_binary_response_settles_completed_without_usage(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = make_service(
            calls,
            upstream=RecordingUpstream(
                calls, result=ok_binary_upstream(b"raw", "audio/mpeg")
            ),
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.handle("embeddings", make_request())
        assert result.is_ok()
        assert billing.settle_statuses == ["completed"]
        assert billing.settle_usages == [None]


class TestMultipartRequestPassthrough:
    """Multipart request bodies forward byte-for-byte (Plan K, Task 2)."""

    def test_rewrite_swaps_model_value_only(self) -> None:
        rewritten = rewrite_multipart_form_field(
            MULTIPART_BODY, MULTIPART_BOUNDARY, "model", "new-model-name"
        )
        expected = MULTIPART_BODY.replace(
            (MODEL + "\r\n").encode("ascii"), b"new-model-name\r\n", 1
        )
        assert rewritten == expected
        assert b'name="image"' in rewritten
        assert b"\x89PNG\r\n\x1a\nBINARY\x00\xffDATA" in rewritten
        assert rewritten.endswith(f"--{MULTIPART_BOUNDARY}--\r\n".encode("ascii"))

    def test_rewrite_leaves_body_unchanged_when_field_missing(self) -> None:
        model_part = b'Content-Disposition: form-data; name="model"\r\n\r\n' + (
            MODEL + "\r\n"
        ).encode("ascii")
        body_without_model = MULTIPART_BODY.replace(model_part, b"", 1)
        assert b'name="model"' not in body_without_model
        rewritten = rewrite_multipart_form_field(
            body_without_model, MULTIPART_BOUNDARY, "model", "new-model-name"
        )
        assert rewritten == body_without_model

    def test_rewrite_missing_boundary_is_verbatim(self) -> None:
        assert (
            rewrite_multipart_form_field(
                MULTIPART_BODY, "no-such-boundary", "model", "x"
            )
            == MULTIPART_BODY
        )

    @pytest.mark.asyncio
    async def test_handle_multipart_rewrites_model_and_forwards_verbatim(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(calls)
        service = make_service(
            calls,
            upstream=upstream,
            model_suffix={"a": ":legacy"},
        )
        request = make_request(
            payload=RelayPassthroughBody.raw(MULTIPART_BODY, MULTIPART_CONTENT_TYPE)
        )
        result = await service.handle("embeddings", request)
        assert result.is_ok()
        assert upstream.captured is not None
        assert upstream.captured.headers == {"content-type": MULTIPART_CONTENT_TYPE}
        expected = rewrite_multipart_form_field(
            MULTIPART_BODY, MULTIPART_BOUNDARY, "model", f"{MODEL}:legacy"
        )
        assert upstream.captured.payload == expected
        assert b"\x89PNG\r\n\x1a\nBINARY\x00\xffDATA" in upstream.captured.payload
        assert b"--bnd-42--\r\n" in upstream.captured.payload

    @pytest.mark.asyncio
    async def test_multipart_without_boundary_forwards_verbatim(self) -> None:
        calls: list[tuple[Any, ...]] = []
        upstream = RequestCapturingUpstream(calls)
        service = make_service(calls, upstream=upstream)
        request = make_request(
            payload=RelayPassthroughBody.raw(
                MULTIPART_BODY, "multipart/form-data; boundary=also-missing"
            )
        )
        result = await service.handle("embeddings", request)
        assert result.is_ok()
        assert upstream.captured is not None
        assert upstream.captured.payload == MULTIPART_BODY

    @pytest.mark.asyncio
    async def test_multipart_request_with_json_response(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(calls)
        request = make_request(
            payload=RelayPassthroughBody.raw(MULTIPART_BODY, MULTIPART_CONTENT_TYPE)
        )
        result = await service.handle("embeddings", request)
        assert result.is_ok()
        assert result.unwrap().payload == default_upstream_response()

    @pytest.mark.asyncio
    async def test_multipart_request_with_binary_response(self) -> None:
        calls: list[tuple[Any, ...]] = []
        audio = b"\x00\xff\xfbMP3"
        service = make_service(
            calls,
            upstream=RecordingUpstream(
                calls, result=ok_binary_upstream(audio, "audio/mpeg")
            ),
        )
        request = make_request(
            payload=RelayPassthroughBody.raw(MULTIPART_BODY, MULTIPART_CONTENT_TYPE)
        )
        result = await service.handle("embeddings", request)
        assert result.is_ok()
        gateway_result = result.unwrap()
        assert gateway_result.body == audio
        assert gateway_result.content_type == "audio/mpeg"
