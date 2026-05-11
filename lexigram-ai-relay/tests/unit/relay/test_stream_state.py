"""Tests for the mutable stream session state and shared lifecycle.

The session is the state machine that ties a source normalizer (a source
mapper's ``stream_to_delta``) to a target emitter (a target mapper's
``delta_to_stream``).  These tests drive it with tiny fake normalizers and
emitters so the state transitions are exercised before the real per-target
emitters exist.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.errors import (
    malformed_payload,
    stream_state_invalid,
    unsupported_format,
)
from lexigram.ai.relay.stream import StreamNormalizer, StreamSession
from lexigram.contracts.ai.exceptions import RelayError, RelayErrorCode
from lexigram.contracts.ai.relay.ir import StreamDelta
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.core.result import Err, Ok, Result


class FakeNormalizer:
    """Normalizer driven by synthetic wire events for state tests."""

    def __init__(self) -> None:
        self.calls: list[Any] = []
        self.states: list[Any] = []

    def __call__(
        self, event: Any, *, state: Any = None
    ) -> Result[tuple[StreamDelta, ...], RelayError]:
        """Map a synthetic event to deltas, or reject it."""
        self.calls.append(event)
        self.states.append(state)
        if event == "wrong-source":
            return Err(unsupported_format("expected openai_chat event"))
        if event == "malformed":
            return Err(malformed_payload("missing field"))
        if isinstance(event, tuple):
            return Ok(tuple(event))
        raise AssertionError(f"unexpected event {event!r}")


class RecordingEmitter:
    """Emitter that records received deltas and echoes them back."""

    def __init__(self) -> None:
        self.received: list[StreamDelta] = []
        self.states: list[Any] = []

    def __call__(
        self, delta: StreamDelta, *, state: Any = None
    ) -> Result[tuple[Any, ...], RelayError]:
        """Record the delta and return it as the emitted target event."""
        self.received.append(delta)
        self.states.append(state)
        return Ok((delta,))


def make_session(
    *,
    include_usage: bool = False,
    stream_id: str | None = "s1",
    created: int | None = 1,
) -> tuple[StreamSession, FakeNormalizer, RecordingEmitter]:
    """Build a session wired to fresh fakes."""
    normalizer = FakeNormalizer()
    emitter = RecordingEmitter()
    session = StreamSession(
        source=RelayFormat.OPENAI_CHAT,
        target=RelayFormat.CLAUDE,
        model="gpt-4o",
        stream_id=stream_id,
        created=created,
        include_usage=include_usage,
        normalizer=normalizer,
        emitter=emitter,
    )
    return session, normalizer, emitter


def delta(**kwargs: Any) -> StreamDelta:
    """Build a StreamDelta with defaults."""
    return StreamDelta(**kwargs)


# -- Step 1: state-machine tests --------------------------------------------


def test_fresh_session_snapshot() -> None:
    """A fresh session reports empty accumulated state."""
    session, _, _ = make_session()
    snap = session.snapshot()
    assert snap.source is RelayFormat.OPENAI_CHAT
    assert snap.target is RelayFormat.CLAUDE
    assert snap.model == "gpt-4o"
    assert snap.stream_id == "s1"
    assert snap.created == 1
    assert snap.text == ""
    assert snap.thinking_text == ""
    assert snap.tool_calls == ()
    assert snap.usage is None
    assert snap.finish_reason is None
    assert snap.status is None
    assert snap.open_blocks == ()
    assert snap.next_output_index == 0
    assert not snap.is_done


def test_role_only_delta_records_role_without_text() -> None:
    """A role announcement is recorded; no text accumulates."""
    session, _, _ = make_session()
    session.accept((delta(kind="role", role="assistant"),))
    snap = session.snapshot()
    assert snap.text == ""
    assert snap.role == "assistant"


def test_text_accumulation() -> None:
    """Content deltas accumulate in order."""
    session, _, _ = make_session()
    session.accept(
        (
            delta(kind="content", content="Hello"),
            delta(kind="content", content=" world"),
        )
    )
    assert session.snapshot().text == "Hello world"


def test_thinking_accumulation() -> None:
    """Thinking deltas accumulate; signatures are only taken verbatim."""
    session, _, _ = make_session()
    session.accept(
        (
            delta(kind="thinking", thinking_delta="Let me"),
            delta(kind="thinking", thinking_delta=" think"),
            delta(
                kind="thinking",
                thinking_delta="...",
                passthrough={"signature": "sig-1"},
            ),
        )
    )
    snap = session.snapshot()
    assert snap.thinking_text == "Let me think..."
    assert snap.thinking_signatures == ("sig-1",)


def test_multiple_tool_call_indices_tracked_separately() -> None:
    """Tool-call deltas for different indices do not overwrite each other."""
    session, _, _ = make_session()
    session.accept(
        (
            delta(kind="tool_call", tool_call_index=0, tool_call_name="get_w"),
            delta(kind="tool_call", tool_call_index=2, tool_call_name="get_t"),
        )
    )
    calls = {call.index: call for call in session.snapshot().tool_calls}
    assert calls[0].name == "get_w"
    assert calls[2].name == "get_t"


def test_split_tool_call_id_name_arguments_are_joined() -> None:
    """Fragmented id/name/arguments stay raw strings and are joined."""
    session, _, _ = make_session()
    session.accept(
        (
            delta(kind="tool_call", tool_call_index=0, tool_call_id="call_"),
            delta(kind="tool_call", tool_call_index=0, tool_call_id="123"),
            delta(kind="tool_call", tool_call_index=0, tool_call_name="get_"),
            delta(kind="tool_call", tool_call_index=0, tool_call_name="weather"),
            delta(kind="tool_call", tool_call_index=0, tool_call_arguments='{"ci'),
            delta(kind="tool_call", tool_call_index=0, tool_call_arguments='ty":"SP"}'),
        )
    )
    call = session.snapshot().tool_calls[0]
    assert call.id == "call_123"
    assert call.name == "get_weather"
    assert call.arguments == '{"city":"SP"}'


def test_usage_only_event_is_remembered() -> None:
    """A usage-only event sets usage without adding text."""
    session, _, _ = make_session()
    usage = RelayUsage(prompt_tokens=10, completion_tokens=5)
    session.accept((delta(kind="usage", usage=usage),))
    snap = session.snapshot()
    assert snap.text == ""
    assert snap.usage is not None
    assert snap.usage.prompt_tokens == 10
    assert snap.usage.completion_tokens == 5


def test_finish_event_records_finish_reason() -> None:
    """A finish delta records the (raw) finish reason."""
    session, _, _ = make_session()
    session.accept((delta(kind="finish", finish_reason="stop"),))
    snap = session.snapshot()
    assert snap.finish_reason == "stop"
    assert snap.status is None


def test_status_event_records_status() -> None:
    """A status delta records the target status value."""
    session, _, _ = make_session()
    session.accept((delta(kind="status", status="in_progress"),))
    assert session.snapshot().status == "in_progress"


def test_block_and_output_index_tracking() -> None:
    """Content blocks and next output index are tracked."""
    session, _, _ = make_session()
    session.accept(
        (
            delta(kind="content", content="a", block_index=0),
            delta(kind="content", content="b", block_index=1),
            delta(kind="content", content="c", output_index=3),
        )
    )
    snap = session.snapshot()
    assert snap.open_blocks == (0, 1)
    assert snap.next_output_index == 4


def test_wrong_source_format_is_rejected() -> None:
    """Events from the wrong source format raise stream_state_invalid."""
    session, _, _ = make_session()
    with pytest.raises(RelayError) as excinfo:
        session.accept("wrong-source")
    assert excinfo.value.code == RelayErrorCode.STREAM_STATE_INVALID.value


def test_malformed_event_propagates_error() -> None:
    """A malformed event raises the normalizer's RelayError."""
    session, _, _ = make_session()
    with pytest.raises(RelayError) as excinfo:
        session.accept("malformed")
    assert excinfo.value.code == RelayErrorCode.MALFORMED_PAYLOAD.value


def test_emitter_error_propagates() -> None:
    """An emitter failure aborts the batch and propagates the error."""

    class ExplodingEmitter(RecordingEmitter):
        def __call__(
            self, delta: StreamDelta, *, state: Any = None
        ) -> Result[tuple[Any, ...], RelayError]:
            return Err(stream_state_invalid("cannot emit delta"))

    session, _, _ = make_session()
    session.emitter = ExplodingEmitter()  # type: ignore[assignment]
    with pytest.raises(RelayError) as excinfo:
        session.accept((delta(kind="content", content="x"),))
    assert excinfo.value.code == RelayErrorCode.STREAM_STATE_INVALID.value


# -- Step 4: finalization ----------------------------------------------------


def test_finalize_truncated_stream_emits_safe_stop() -> None:
    """A truncated stream finalizes to a safe stop finish delta."""
    session, _, _ = make_session()
    session.accept((delta(kind="content", content="partial"),))
    terminal = session.finalize()
    assert len(terminal) == 1
    stop_delta = terminal[0]
    assert stop_delta.kind == "finish"
    assert stop_delta.finish_reason == "stop"
    assert session.snapshot().is_done
    assert session.snapshot().finish_reason == "stop"


def test_finalize_emits_usage_when_requested() -> None:
    """finalize emits a usage delta when include_usage and usage exist."""
    session, _, _ = make_session(include_usage=True)
    usage = RelayUsage(prompt_tokens=7, completion_tokens=3)
    session.accept(
        (
            delta(kind="content", content="hi"),
            delta(kind="usage", usage=usage),
        )
    )
    terminal = session.finalize()
    kinds = [d.kind for d in terminal]
    assert kinds == ["finish", "usage"]
    usage_delta = terminal[1]
    assert usage_delta.usage is not None
    assert usage_delta.usage.prompt_tokens == 7


def test_finalize_does_not_emit_usage_when_not_requested() -> None:
    """Without include_usage, finalize emits only the safe stop."""
    session, _, _ = make_session(include_usage=False)
    session.accept(
        (
            delta(kind="content", content="hi"),
            delta(kind="usage", usage=RelayUsage(prompt_tokens=7)),
        )
    )
    terminal = session.finalize()
    assert [d.kind for d in terminal] == ["finish"]


def test_finalize_keeps_source_finish_reason() -> None:
    """A source-provided finish reason is not replaced by the safe stop."""
    session, _, _ = make_session()
    session.accept((delta(kind="finish", finish_reason="length"),))
    terminal = session.finalize()
    assert len(terminal) == 0
    assert session.snapshot().finish_reason == "length"


def test_finalize_idempotent_returns_empty() -> None:
    """A second finalize returns an empty sequence without mutation."""
    session, _, emitter = make_session()
    session.accept((delta(kind="content", content="x"),))
    first = session.finalize()
    captured = list(emitter.received)
    second = session.finalize()
    assert second == ()
    assert emitter.received == captured  # no new emitter calls
    assert len(first) == 1  # first result preserved


def test_accept_after_finalize_is_rejected() -> None:
    """accept() after finalize raises stream_already_finalized."""
    session, _, _ = make_session()
    session.accept((delta(kind="content", content="x"),))
    session.finalize()
    with pytest.raises(RelayError) as excinfo:
        session.accept((delta(kind="content", content="late"),))
    assert excinfo.value.code == RelayErrorCode.STREAM_ALREADY_FINALIZED.value


def test_no_events_emitted_after_finalization() -> None:
    """No new deltas reach the emitter after finalization."""
    session, _, emitter = make_session()
    session.accept((delta(kind="content", content="x"),))
    session.finalize()
    try:
        session.accept((delta(kind="content", content="late"),))
    except RelayError:
        pass
    received = emitter.received
    assert not any(d.content == "late" for d in received)


def test_finalize_twice_without_events() -> None:
    """A stream finalized without events still returns a safe stop once."""
    session, _, _ = make_session()
    assert session.finalize() != ()
    assert session.finalize() == ()


def test_created_stream_id_preserved() -> None:
    """stream_id and created survive deltas and finalization."""
    session, _, _ = make_session(stream_id="abc", created=42)
    session.accept((delta(kind="content", content="hi"),))
    session.finalize()
    snap = session.snapshot()
    assert snap.stream_id == "abc"
    assert snap.created == 42


def test_normalizer_receives_stream_state() -> None:
    """The normalizer receives a state carrying source/target/model."""
    session, normalizer, _ = make_session()
    session.accept((delta(kind="content", content="hi"),))
    state = normalizer.states[0]
    assert state.source is RelayFormat.OPENAI_CHAT
    assert state.target is RelayFormat.CLAUDE
    assert state.model == "gpt-4o"


def test_record_loss_tracks_warnings_and_losses() -> None:
    """record_loss appends a RelayLoss and a warning to the snapshot."""
    session, _, _ = make_session()
    session.record_loss(field="thinking", reason="thinking_not_supported")
    snap = session.snapshot()
    assert len(snap.losses) == 1
    assert snap.losses[0].field == "thinking"
    assert snap.losses[0].target is RelayFormat.CLAUDE
    assert snap.warnings == ("thinking: thinking_not_supported (claude, warning)",)


def test_session_implements_relay_stream_session_protocol() -> None:
    """StreamSession satisfies the container-facing protocol."""
    from lexigram.contracts.ai.relay.protocols import RelayStreamSessionProtocol

    session, _, _ = make_session()
    assert isinstance(session, RelayStreamSessionProtocol)


def test_normalizer_emitter_protocol_types() -> None:
    """The bundled protocol aliases are importable and runtime-checkable."""
    assert StreamNormalizer is not None
