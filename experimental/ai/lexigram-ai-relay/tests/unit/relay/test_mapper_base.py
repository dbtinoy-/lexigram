"""Tests for the mapper infrastructure and conversion context normalization."""
from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.exceptions import RelayError, RelayErrorCode
from lexigram.contracts.ai.relay.context import (
    RelayConversionContext,
    RelayOptions,
)
from lexigram.contracts.ai.relay.ir import RelayRequest, RelayResponse, StreamDelta, StreamState
from lexigram.contracts.ai.relay.types import RelayFormat, RelayLoss
from lexigram.contracts.core.result import Ok, Result

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import (
    malformed_payload,
    media_resolution_required,
    missing_required_option,
    translate,
    unsupported_feature,
    unsupported_format,
)
from lexigram.ai.relay.mappers.base import FormatMapper, record_loss, warning_messages


class FakeMapper(FormatMapper):
    """Structural fake exercising every mapper operation."""

    def request_to_ir(
        self, payload: Any, *, context: ConversionContext
    ) -> Result[RelayRequest, RelayError]:
        return Ok(RelayRequest(model="gpt-4o", messages=[]))

    def ir_to_request(
        self, request: RelayRequest, *, context: ConversionContext
    ) -> Result[Any, RelayError]:
        return Ok(request.model)

    def response_to_ir(
        self, payload: Any, *, context: ConversionContext
    ) -> Result[RelayResponse, RelayError]:
        return Ok(RelayResponse(model="gpt-4o"))

    def ir_to_response(
        self, response: RelayResponse, *, context: ConversionContext
    ) -> Result[Any, RelayError]:
        return Ok(response.model)

    def stream_to_delta(
        self, event: Any, *, state: StreamState
    ) -> Result[tuple[StreamDelta, ...], RelayError]:
        return Ok((StreamDelta(content="x"),))

    def delta_to_stream(
        self, delta: StreamDelta, *, state: StreamState
    ) -> Result[tuple[Any, ...], RelayError]:
        return Ok((delta.content,))


def test_format_mapper_protocol_implementable_by_structural_fake() -> None:
    """A structural fake can implement the typed FormatMapper protocol."""
    mapper = FakeMapper()
    assert isinstance(mapper, FormatMapper)
    request = mapper.request_to_ir({}, context=ConversionContext()).unwrap()
    assert request.model == "gpt-4o"
    response = mapper.response_to_ir({}, context=ConversionContext()).unwrap()
    assert response.model == "gpt-4o"
    state = StreamState(
        source=RelayFormat.OPENAI_CHAT,
        target=RelayFormat.CLAUDE,
        model="gpt-4o",
    )
    deltas = mapper.stream_to_delta({}, state=state).unwrap()
    assert deltas[0].content == "x"


def test_context_wrap_none_is_nil_safe() -> None:
    """A None host context yields safe zero-value options and callbacks."""
    context = ConversionContext.wrap(None)
    assert context.options == RelayOptions()
    assert context.default_max_tokens("claude-sonnet-4-5") is None
    assert context.safety_setting("HARM_CATEGORY_HATE_SPEECH") is None
    assert context.supports_image_generation("gemini-2.5-pro") is False
    assert context.preserve_thinking_suffix("qwen3") is False
    assert context.media_resolver is None
    assert context.losses == []


def test_context_wrap_preserves_host_callbacks() -> None:
    """Host callbacks and options are wired through the adapter."""

    def default_max_tokens(model: str) -> int | None:
        return 4096 if model.startswith("claude") else None

    def safety_setting(category: str) -> str | None:
        return "BLOCK_NONE" if category == "HARM_CATEGORY_HATE_SPEECH" else None

    host = RelayConversionContext(
        default_max_tokens=default_max_tokens,
        safety_setting=safety_setting,
        supports_image_generation=lambda model: model.startswith("gemini"),
        preserve_thinking_suffix=lambda model: model.startswith("qwen"),
    )
    context = ConversionContext.wrap(host)
    assert context.max_tokens_for("claude-sonnet-4-5") == 4096
    assert context.max_tokens_for("gpt-4o") is None
    assert context.safety_setting("HARM_CATEGORY_HATE_SPEECH") == "BLOCK_NONE"
    assert context.supports_image_generation("gemini-2.5-pro") is True
    assert context.preserve_thinking_suffix("qwen3") is True


def test_context_rejects_negative_default_max_tokens() -> None:
    """Negative or absent default max_tokens normalize to None."""
    host = RelayConversionContext(default_max_tokens=lambda model: -1)
    assert ConversionContext.wrap(host).max_tokens_for("claude-sonnet-4-5") is None


def test_context_normalizes_model_without_selecting() -> None:
    """Model names are cleaned but never remapped."""
    context = ConversionContext.wrap(None)
    assert context.normalize_model("  gpt-4o  ") == "gpt-4o"
    assert context.normalize_model("claude-sonnet-4-5") == "claude-sonnet-4-5"


def test_record_loss_appends_relay_loss() -> None:
    """record_loss appends a structured RelayLoss to the context."""
    context = ConversionContext.wrap(None)
    record_loss(
        context,
        field="max_tokens",
        target=RelayFormat.CLAUDE,
        reason="max_tokens_conflict",
    )
    assert len(context.losses) == 1
    loss = context.losses[0]
    assert loss.field == "max_tokens"
    assert loss.target is RelayFormat.CLAUDE
    assert loss.reason == "max_tokens_conflict"
    assert loss.severity == "warning"


def test_losses_flow_from_host_context() -> None:
    """Losses appended on the host context are visible to the adapter."""
    host = RelayConversionContext()
    context = ConversionContext.wrap(host)
    record_loss(context, field="thinking", target=RelayFormat.GEMINI, reason="unsupported")
    assert len(host.losses) == 1
    assert host.losses[0].reason == "unsupported"


def test_warning_messages_extract_losses() -> None:
    """Loss records render into stable warning strings."""
    context = ConversionContext.wrap(None)
    record_loss(
        context,
        field="max_tokens",
        target=RelayFormat.CLAUDE,
        reason="max_tokens_conflict",
        severity="error",
    )
    record_loss(context, field="top_k", target=RelayFormat.OPENAI_CHAT, reason="dropped")
    warnings = warning_messages(context.losses)
    assert warnings[0] == "max_tokens: max_tokens_conflict (claude, error)"
    assert warnings[1] == "top_k: dropped (openai_chat, warning)"


def test_malformed_payload_error_code() -> None:
    """Malformed DTO fields become stable malformed_payload errors."""
    error = malformed_payload("choices[0].message is not a dict")
    assert isinstance(error, RelayError)
    assert error.code == RelayErrorCode.MALFORMED_PAYLOAD.value


def test_missing_max_tokens_error_code() -> None:
    """A missing Claude max_tokens becomes a missing_required_option error."""
    error = missing_required_option("claude requires max_tokens")
    assert error.code == RelayErrorCode.MISSING_REQUIRED_OPTION.value


def test_unsupported_stream_event_error_code() -> None:
    """An unsupported stream event type becomes an unsupported_feature error."""
    error = unsupported_feature("stream event type 'error' is not supported")
    assert error.code == RelayErrorCode.UNSUPPORTED_FEATURE.value


def test_wrong_source_dto_error_code() -> None:
    """A wrong source DTO type becomes an unsupported_format error."""
    error = unsupported_format("expected GeminiRequest, got OpenAIChatRequest")
    assert error.code == RelayErrorCode.UNSUPPORTED_FORMAT.value


def test_missing_media_error_code() -> None:
    """Missing media resolution becomes a media_resolution_required error."""
    error = media_resolution_required("no media resolver supplied for https://...")
    assert error.code == RelayErrorCode.MEDIA_RESOLUTION_REQUIRED.value


def test_translate_maps_dto_exceptions_to_malformed_payload() -> None:
    """ValueError/TypeError from DTO parsing map to malformed_payload."""
    error = translate(ValueError("bad json"), detail="gemini contents[0]")
    assert error.code == RelayErrorCode.MALFORMED_PAYLOAD.value


def test_translate_passes_relay_errors_through() -> None:
    """RelayError instances pass through translation unchanged."""
    original = unsupported_feature("stream not supported")
    translated = translate(original, detail="stream")
    assert translated is original
    assert translated.code == RelayErrorCode.UNSUPPORTED_FEATURE.value
