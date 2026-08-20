"""Tests for the passthrough upstream response carrier."""

from __future__ import annotations

from lexigram.ai.relay.gateway.passthrough import RelayPassthroughResult


class TestRelayPassthroughResult:
    """``RelayPassthroughResult`` construction and value semantics."""

    def test_carries_body_content_type_status(self) -> None:
        result = RelayPassthroughResult(
            body=b"\x00\xff", content_type="audio/mpeg", status_code=200
        )
        assert result.body == b"\x00\xff"
        assert result.content_type == "audio/mpeg"
        assert result.status_code == 200
        assert result.payload is None
        assert result.headers == {}

    def test_defaults_are_empty_body_and_ok_status(self) -> None:
        result = RelayPassthroughResult()
        assert result.body == b""
        assert result.content_type == ""
        assert result.status_code == 200
        assert result.headers == {}
        assert result.payload is None
        assert result.stream is None
        assert result.metadata is None

    def test_options_headers_payload_metadata(self) -> None:
        result = RelayPassthroughResult(
            body=b"{}",
            content_type="application/json",
            headers={"x-request-id": "req-1"},
            payload={"object": "list"},
        )
        assert result.headers == {"x-request-id": "req-1"}
        assert result.payload == {"object": "list"}

    def test_is_frozen(self) -> None:
        result = RelayPassthroughResult(body=b"data")
        try:
            result.body = b"other"  # type: ignore[misc]
        except Exception:
            pass
        else:
            raise AssertionError("RelayPassthroughResult must be frozen")
        assert result.body == b"data"