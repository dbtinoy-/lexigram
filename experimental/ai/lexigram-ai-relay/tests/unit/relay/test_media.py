"""Tests for pure data-URI decoding and media resolver delegation."""

from __future__ import annotations

import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.media import decode_data_uri, resolve_media
from lexigram.contracts.ai.exceptions import RelayError, RelayErrorCode
from lexigram.contracts.ai.relay.types import RelayFormat
from lexigram.contracts.core.result import Err, Ok

_PNG = "iVBORw0KGgoAAAANSUhEUg=="
_DOG_URI = f"data:image/png;base64,{_PNG}"


class FakeResolver:
    """Structural media resolver returning a fixed base64 payload."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[str] = []

    def resolve(self, url: str) -> object:
        self.calls.append(url)
        if self.fail:
            return Err(RelayError("boom", code=RelayErrorCode.SERIALIZATION_ERROR))
        return Ok(("image/png", "AAAB"))


# -- decode_data_uri ----------------------------------------------------------


def test_decode_valid_base64_data_uri() -> None:
    """A well-formed base64 data URI decodes to media type and data."""
    result = decode_data_uri(_DOG_URI)
    assert result.is_ok()
    media_type, data = result.unwrap()
    assert media_type == "image/png"
    assert data == _PNG


def test_decode_preserves_raw_data_without_prefix() -> None:
    """Decoded data is raw base64, never wrapped in a data URI."""
    result = decode_data_uri(_DOG_URI)
    assert result.unwrap() == ("image/png", _PNG)


def test_decode_rejects_non_data_scheme() -> None:
    """A URL is not a data URI and is rejected with serialization_error."""
    result = decode_data_uri("https://example.com/cat.png")
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.SERIALIZATION_ERROR


def test_decode_rejects_missing_base64_token() -> None:
    """A data URI without the ;base64 marker is malformed."""
    result = decode_data_uri("data:image/png,")
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.SERIALIZATION_ERROR


def test_decode_rejects_empty_payload() -> None:
    """A data URI with empty base64 data is rejected."""
    result = decode_data_uri("data:image/png;base64,")
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.SERIALIZATION_ERROR


def test_decode_rejects_empty_uri() -> None:
    """An empty string is rejected as malformed."""
    result = decode_data_uri("")
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.SERIALIZATION_ERROR


def test_decode_rejects_invalid_base64() -> None:
    """Base64 data that is not decodable is rejected."""
    result = decode_data_uri("data:image/png;base64,!!!not-base64!!!")
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.SERIALIZATION_ERROR


def test_decode_accepts_common_media_types() -> None:
    """JPEG, GIF, and webp data URIs decode like PNG."""
    for mime in ("image/jpeg", "image/gif", "image/webp"):
        result = decode_data_uri(f"data:{mime};base64,{_PNG}")
        assert result.is_ok()
        assert result.unwrap()[0] == mime


# -- resolve_media ------------------------------------------------------------


def test_resolve_data_uri_without_resolver() -> None:
    """Data URIs decode without a resolver present."""
    result = resolve_media(_DOG_URI, ConversionContext(), field="content", target=RelayFormat.OPENAI_CHAT)
    assert result.is_ok()
    assert result.unwrap() == ("image/png", _PNG)


def test_resolve_url_calls_resolver() -> None:
    """URL content delegates to the context resolver."""
    resolver = FakeResolver()
    ctx = ConversionContext(media_resolver=resolver)
    result = resolve_media("https://example.com/cat.png", ctx, field="content", target=RelayFormat.CLAUDE)
    assert result.is_ok()
    assert result.unwrap() == ("image/png", "AAAB")
    assert resolver.calls == ["https://example.com/cat.png"]


def test_resolve_url_without_resolver_is_media_resolution_required() -> None:
    """A URL without a resolver yields media_resolution_required."""
    result = resolve_media(
        "https://example.com/cat.png",
        ConversionContext(),
        field="messages[0].image",
        target=RelayFormat.GEMINI,
    )
    assert result.is_err()
    error = result.unwrap_err()
    assert error.code == RelayErrorCode.MEDIA_RESOLUTION_REQUIRED
    assert "messages[0].image" in str(error)


def test_resolve_url_lossy_fallback_records_loss() -> None:
    """Lossy fallback records a loss instead of failing hard."""
    ctx = ConversionContext()
    result = resolve_media(
        "https://example.com/cat.png",
        ctx,
        field="messages[0].image",
        target=RelayFormat.GEMINI,
        lossy=True,
    )
    assert result.is_ok()
    assert result.unwrap() is None
    assert any(loss.reason == "media_unresolved_dropped" for loss in ctx.losses)


def test_resolve_url_lossy_off_does_not_record_loss() -> None:
    """Non-lossy failure records no loss."""
    ctx = ConversionContext()
    result = resolve_media(
        "https://example.com/cat.png",
        ctx,
        field="messages[0].image",
        target=RelayFormat.GEMINI,
    )
    assert result.is_err()
    assert ctx.losses == []


def test_resolve_propagates_resolver_failure_with_field() -> None:
    """Resolver failures propagate as RelayError carrying the source field."""
    resolver = FakeResolver(fail=True)
    ctx = ConversionContext(media_resolver=resolver)
    result = resolve_media(
        "https://example.com/cat.png", ctx, field="content[0]", target=RelayFormat.CLAUDE
    )
    assert result.is_err()
    error = result.unwrap_err()
    assert error.code == RelayErrorCode.SERIALIZATION_ERROR
    assert "content[0]" in str(error)


def test_media_module_never_imports_network_libraries() -> None:
    """The media module must not pull in network client libraries."""
    import sys

    import lexigram.ai.relay.media as media

    source = open(media.__file__, encoding="utf-8").read()
    for forbidden in ("urllib", "requests", "httpx", "aiohttp", "socket"):
        assert forbidden not in source, f"{forbidden} must not be used"
    assert "http.client" not in source


@pytest.fixture
def ctx() -> ConversionContext:
    """A fresh conversion context per test."""
    return ConversionContext()
