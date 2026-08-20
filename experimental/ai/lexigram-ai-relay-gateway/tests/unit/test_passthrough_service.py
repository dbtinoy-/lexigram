"""Passthrough service tests (Relay Gateway Plan J, Task 2).

Verifies the no-conversion lifecycle of ``PassthroughService``: channel
selection by endpoint kind, verbatim body forwarding with model-suffix
substitution, authorization/billing hook ordering, and error
classification — all mirroring the buffered chat pipeline without
``RelayConverterProtocol`` involvement.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.gateway.passthrough import (
    RelayPassthroughBody,
    rewrite_multipart_form_field,
)
from lexigram.contracts.ai.relay import (
    RelayGatewayError,
    RelayUsage,
)
from lexigram.result import Err
from passthrough_test_helpers import (
    BASE_URL,
    MODEL,
    MULTIPART_BODY,
    MULTIPART_BOUNDARY,
    MULTIPART_CONTENT_TYPE,
    REQUEST_ID,
    TENANT_ID,
    WHITESPACE_BODY,
    FailingSettling,
    RecordingAuthorizer,
    RecordingBilling,
    RecordingUpstream,
    RequestCapturingUpstream,
    default_channels,
    default_upstream_response,
    make_channel,
    make_request,
    make_service,
    ok_binary_upstream,
    ok_upstream,
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
        assert gateway_result.payload == default_upstream_response()
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
        service = make_service(
            calls,
            authorizer=RecordingAuthorizer(calls),
            billing=FailingSettling(calls),
        )
        result = await service.handle("embeddings", make_request())
        assert result.is_ok()


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


class TestMultipartDispatch:
    """Raw multipart bodies travel through the service byte-for-byte."""

    @pytest.mark.asyncio
    async def test_handle_multipart_rewrites_model_and_forwards_verbatim(
        self,
    ) -> None:
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