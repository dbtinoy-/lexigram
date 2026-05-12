"""Relay gateway codec and upstream adapter tests (Relay Gateway plan, Task 3).

Verifies wire JSON decode/encode across all four relay formats
(``RelayPayloadCodec``) and the ``HTTPClientProtocol``-backed upstream
adapter's success and error classification (``HTTPUpstreamAdapter``).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.relay import (
    ClaudeRequest,
    GeminiRequest,
    OpenAIChatRequest,
    RelayFormat,
    RelayGatewayError,
    ResponsesRequest,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.exceptions import InfrastructureError
from lexigram.contracts.web import HttpResponse
from lexigram.serialization import dumps, loads


class FakeHTTPClient:
    """Minimal ``HTTPClientProtocol`` double used by the adapter tests.

    Records every outbound call and either returns the canned response
    or raises the configured error.
    """

    def __init__(
        self,
        response: HttpResponse | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def request(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        """Record the call; return the canned response or raise."""
        self.calls.append({"method": method, "url": url, **kwargs})
        if self.error is not None:
            raise self.error
        if self.response is None:
            raise AssertionError("FakeHTTPClient needs a response or an error")
        return self.response


def make_upstream_request(
    method: str = "POST",
    url: str = "https://upstream/v1/chat/completions",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = 60.0,
    request_id: str = "req-1",
) -> UpstreamRequest:
    """Build an ``UpstreamRequest`` with provider-neutral defaults."""
    return UpstreamRequest(
        request_id=request_id,
        method=method,
        url=url,
        headers=headers if headers is not None else {"authorization": "Bearer secret"},
        payload=payload if payload is not None else {"model": "gpt-4o"},
        timeout_seconds=timeout_seconds,
    )


def make_codec() -> RelayPayloadCodec:
    """Build a fresh codec instance."""
    return RelayPayloadCodec()


def make_adapter(fake: FakeHTTPClient) -> HTTPUpstreamAdapter:
    """Build an adapter over the given fake HTTP client."""
    return HTTPUpstreamAdapter(fake)


class TestRelayPayloadCodecDecode:
    """Wire decode: DTO selection, passthrough, and error classification."""

    @pytest.mark.parametrize(
        ("format_", "dto_cls", "wire"),
        [
            (
                RelayFormat.OPENAI_CHAT,
                OpenAIChatRequest,
                {
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": "hi"}],
                    "x_custom": 1,
                },
            ),
            (
                RelayFormat.OPENAI_RESPONSES,
                ResponsesRequest,
                {
                    "model": "gpt-4o",
                    "input": [{"role": "user", "content": "hi"}],
                    "x_custom": 1,
                },
            ),
            (
                RelayFormat.CLAUDE,
                ClaudeRequest,
                {
                    "model": "claude-3-5-sonnet",
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": "hi"}],
                    "x_custom": 1,
                },
            ),
            (
                RelayFormat.GEMINI,
                GeminiRequest,
                {
                    "contents": [{"role": "user", "parts": [{"text": "hi"}]}],
                    "x_custom": 1,
                },
            ),
        ],
    )
    def test_valid_payload_decodes_to_typed_dto(
        self,
        format_: RelayFormat,
        dto_cls: type[Any],
        wire: dict[str, Any],
    ) -> None:
        result = make_codec().decode_request(format_, dumps(wire), "req-1")
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, dto_cls)
        assert dto.passthrough == {"x_custom": 1}

    def test_openai_chat_fields_present(self) -> None:
        wire = {"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]}
        dto = make_codec().decode_request(
            RelayFormat.OPENAI_CHAT, dumps(wire), "req-1"
        ).unwrap()
        assert dto.model == "gpt-4o"
        assert dto.messages[0].role == "user"
        assert dto.messages[0].content == "hi"

    def test_responses_fields_present(self) -> None:
        wire = {"model": "gpt-4o", "input": [{"role": "user", "content": "hi"}]}
        dto = make_codec().decode_request(
            RelayFormat.OPENAI_RESPONSES, dumps(wire), "req-1"
        ).unwrap()
        assert dto.model == "gpt-4o"
        assert dto.input[0].role == "user"
        assert dto.input[0].content == "hi"

    def test_claude_fields_present(self) -> None:
        wire = {
            "model": "claude-3-5-sonnet",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": "hi"}],
        }
        dto = make_codec().decode_request(
            RelayFormat.CLAUDE, dumps(wire), "req-1"
        ).unwrap()
        assert dto.model == "claude-3-5-sonnet"
        assert dto.max_tokens == 1024
        assert dto.messages[0].content[0].text == "hi"

    def test_gemini_fields_present(self) -> None:
        wire = {"contents": [{"role": "user", "parts": [{"text": "hi"}]}]}
        dto = make_codec().decode_request(
            RelayFormat.GEMINI, dumps(wire), "req-1"
        ).unwrap()
        assert dto.contents[0].role == "user"
        assert dto.contents[0].parts[0].text == "hi"

    @pytest.mark.parametrize(
        ("format_", "wire", "field"),
        [
            (RelayFormat.OPENAI_CHAT, {"messages": []}, "model"),
            (RelayFormat.OPENAI_RESPONSES, {"input": []}, "model"),
            (RelayFormat.CLAUDE, {"model": "x", "messages": []}, "max_tokens"),
            (RelayFormat.GEMINI, {}, "contents"),
        ],
    )
    def test_missing_required_field_is_invalid_request(
        self, format_: RelayFormat, wire: dict[str, Any], field: str
    ) -> None:
        result = make_codec().decode_request(format_, dumps(wire), "req-42")
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "INVALID_REQUEST"
        assert err.status_code == 400
        assert field in err.message
        assert err.request_id == "req-42"

    def test_malformed_json_is_invalid_request(self) -> None:
        result = make_codec().decode_request(
            RelayFormat.OPENAI_CHAT, b"{not json", "req-7"
        )
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "INVALID_REQUEST"
        assert err.message == "malformed JSON"
        assert err.status_code == 400
        assert err.request_id == "req-7"

    @pytest.mark.parametrize("raw", [b"[1,2]", b'"str"'])
    def test_non_object_root_is_invalid_request(self, raw: bytes) -> None:
        result = make_codec().decode_request(RelayFormat.OPENAI_CHAT, raw, "req-7")
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "INVALID_REQUEST"
        assert err.message == "payload must be a JSON object"
        assert err.status_code == 400
        assert err.request_id == "req-7"

    def test_unknown_format_is_unsupported(self) -> None:
        result = make_codec().decode_request(
            "bogus_format", dumps({"model": "gpt-4o"}), "req-8"
        )
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "UNSUPPORTED_FORMAT"
        assert err.status_code == 400
        assert err.request_id == "req-8"


class TestRelayPayloadCodecEncode:
    """Wire encode: ``None`` omission and falsey-but-present values."""

    def test_none_optional_fields_are_omitted(self) -> None:
        wire = {"model": "gpt-4o", "messages": []}
        dto = make_codec().decode_request(
            RelayFormat.OPENAI_CHAT, dumps(wire), "req-1"
        ).unwrap()
        encoded = make_codec().encode(dto)
        assert encoded.is_ok()
        parsed = loads(encoded.unwrap())
        assert "temperature" not in parsed
        assert "top_p" not in parsed
        assert "tools" not in parsed

    def test_false_zero_and_empty_list_are_preserved(self) -> None:
        wire = {
            "model": "gpt-4o",
            "messages": [],
            "stream": False,
            "temperature": 0.0,
            "tools": [],
        }
        dto = make_codec().decode_request(
            RelayFormat.OPENAI_CHAT, dumps(wire), "req-1"
        ).unwrap()
        encoded = make_codec().encode(dto)
        assert encoded.is_ok()
        assert loads(encoded.unwrap()) == wire

    def test_passthrough_fields_survive_encode(self) -> None:
        wire = {"model": "gpt-4o", "messages": [], "x_custom": 1}
        dto = make_codec().decode_request(
            RelayFormat.OPENAI_CHAT, dumps(wire), "req-1"
        ).unwrap()
        encoded = make_codec().encode(dto)
        assert encoded.is_ok()
        assert loads(encoded.unwrap())["x_custom"] == 1

    def test_unserializable_payload_is_encode_failed(self) -> None:
        cyclic: list[Any] = []
        cyclic.append(cyclic)
        dto = OpenAIChatRequest(
            model="gpt-4o", messages=[], passthrough={"bad": cyclic}
        )
        result = make_codec().encode(dto)
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "ENCODE_FAILED"
        assert err.status_code == 500
        assert err.request_id == ""


class TestHTTPUpstreamAdapterSuccess:
    """2xx responses map to ``Ok(UpstreamResponse)`` with header passthrough."""

    async def test_200_json_body_round_trips(self) -> None:
        fake = FakeHTTPClient(
            response=HttpResponse(
                status=200,
                headers={"content-type": "application/json"},
                body=dumps({"id": "resp-1", "choices": []}),
            )
        )
        result = await make_adapter(fake).request(make_upstream_request())
        assert result.is_ok()
        upstream = result.unwrap()
        assert isinstance(upstream, UpstreamResponse)
        assert upstream.status_code == 200
        assert upstream.headers == {"content-type": "application/json"}
        assert upstream.payload == {"id": "resp-1", "choices": []}

    async def test_200_empty_body_yields_none_payload(self) -> None:
        fake = FakeHTTPClient(response=HttpResponse(status=200, body=b""))
        result = await make_adapter(fake).request(make_upstream_request())
        assert result.is_ok()
        assert result.unwrap().payload is None

    async def test_204_yields_none_payload(self) -> None:
        fake = FakeHTTPClient(response=HttpResponse(status=204, body=b""))
        result = await make_adapter(fake).request(make_upstream_request())
        assert result.is_ok()
        assert result.unwrap().status_code == 204
        assert result.unwrap().payload is None

    async def test_request_kwargs_are_forwarded(self) -> None:
        request = make_upstream_request(
            headers={"authorization": "Bearer abc"},
            payload={"model": "gpt-4o"},
            timeout_seconds=30.0,
        )
        fake = FakeHTTPClient(response=HttpResponse(status=200, body=b""))
        result = await make_adapter(fake).request(request)
        assert result.is_ok()
        assert fake.calls == [
            {
                "method": "POST",
                "url": "https://upstream/v1/chat/completions",
                "headers": {"authorization": "Bearer abc"},
                "json": {"model": "gpt-4o"},
                "timeout": 30.0,
                "channel_name": "",
            }
        ]


class TestHTTPUpstreamAdapterErrors:
    """Non-2xx responses and transport failures map to typed errors."""

    async def _request_with(
        self,
        response: HttpResponse | None = None,
        error: BaseException | None = None,
        request: UpstreamRequest | None = None,
    ) -> RelayGatewayError:
        fake = FakeHTTPClient(response=response, error=error)
        result = await make_adapter(fake).request(request or make_upstream_request())
        assert result.is_err()
        return result.unwrap_err()

    async def test_429_is_non_retryable_upstream_error(self) -> None:
        err = await self._request_with(
            response=HttpResponse(
                status=429, body=dumps({"error": {"message": "rate limited"}})
            )
        )
        assert isinstance(err, RelayGatewayError)
        assert err.code == "UPSTREAM_ERROR"
        assert err.status_code == 429
        assert err.retryable is False
        assert err.message == "rate limited"
        assert err.request_id == "req-1"

    async def test_502_is_retryable_upstream_error(self) -> None:
        err = await self._request_with(
            response=HttpResponse(status=502, body=dumps({"error": "bad gateway"}))
        )
        assert isinstance(err, RelayGatewayError)
        assert err.code == "UPSTREAM_ERROR"
        assert err.status_code == 502
        assert err.retryable is True
        assert err.message == "bad gateway"

    async def test_plain_message_key_is_used_when_error_key_absent(self) -> None:
        err = await self._request_with(
            response=HttpResponse(status=400, body=dumps({"message": "no model"}))
        )
        assert isinstance(err, RelayGatewayError)
        assert err.code == "UPSTREAM_ERROR"
        assert err.message == "no model"

    async def test_error_message_never_leaks_body_content(self) -> None:
        err = await self._request_with(
            response=HttpResponse(
                status=429,
                body=dumps(
                    {
                        "error": {"message": "rate limited"},
                        "details": "super-secret-token",
                    }
                ),
            )
        )
        assert err.message == "rate limited"
        assert "super-secret-token" not in str(err)
        assert "super-secret-token" not in err.message

    async def test_error_message_falls_back_when_body_is_malformed(self) -> None:
        err = await self._request_with(
            response=HttpResponse(status=429, body=b"{not json")
        )
        assert err.message == "upstream request failed"
        assert err.status_code == 429

    async def test_error_message_falls_back_without_public_keys(self) -> None:
        err = await self._request_with(
            response=HttpResponse(status=400, body=dumps({"details": "opaque"}))
        )
        assert err.message == "upstream request failed"
        assert err.status_code == 400

    async def test_error_message_falls_back_on_non_object_body(self) -> None:
        err = await self._request_with(
            response=HttpResponse(status=400, body=b"[1,2]")
        )
        assert err.message == "upstream request failed"
        assert err.status_code == 400

    async def test_status_outside_400_to_599_maps_to_502(self) -> None:
        err = await self._request_with(response=HttpResponse(status=600, body=b""))
        assert isinstance(err, RelayGatewayError)
        assert err.code == "UPSTREAM_ERROR"
        assert err.status_code == 502

    async def test_malformed_json_on_200_is_upstream_malformed(self) -> None:
        err = await self._request_with(
            response=HttpResponse(status=200, body=b"{not json")
        )
        assert isinstance(err, RelayGatewayError)
        assert err.code == "UPSTREAM_MALFORMED"
        assert err.status_code == 502
        assert err.request_id == "req-1"

    async def test_non_object_root_on_200_is_upstream_malformed(self) -> None:
        err = await self._request_with(
            response=HttpResponse(status=200, body=b"[1,2]")
        )
        assert isinstance(err, RelayGatewayError)
        assert err.code == "UPSTREAM_MALFORMED"
        assert err.status_code == 502

    async def test_timeout_maps_to_504_retryable(self) -> None:
        err = await self._request_with(error=TimeoutError("upstream timed out"))
        assert isinstance(err, RelayGatewayError)
        assert err.code == "UPSTREAM_TIMEOUT"
        assert err.status_code == 504
        assert err.retryable is True
        assert err.request_id == "req-1"

    async def test_cancellation_maps_to_499(self) -> None:
        err = await self._request_with(error=asyncio.CancelledError())
        assert isinstance(err, RelayGatewayError)
        assert err.code == "UPSTREAM_CANCELLED"
        assert err.status_code == 499

    async def test_infrastructure_error_maps_to_502_retryable(self) -> None:
        err = await self._request_with(error=InfrastructureError("boom"))
        assert isinstance(err, RelayGatewayError)
        assert err.code == "UPSTREAM_FAILED"
        assert err.status_code == 502
        assert err.retryable is True

    async def test_request_id_threaded_through_transport_errors(self) -> None:
        request = make_upstream_request(request_id="req-77")
        fake = FakeHTTPClient(error=InfrastructureError("boom"))
        result = await make_adapter(fake).request(request)
        assert result.is_err()
        assert result.unwrap_err().request_id == "req-77"
