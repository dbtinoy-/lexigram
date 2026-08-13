"""Mutable stream session state and shared lifecycle rules.

The session is the state machine shared by every target emitter.  It
accepts one source wire event at a time (producing zero or more
``StreamDelta`` objects), applies deltas in order, hands each delta to
the configured target emitter, and finalizes idempotently when the
upstream stream truncates or completes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from lexigram.ai.relay.errors import stream_already_finalized, stream_state_invalid
from lexigram.contracts.ai.exceptions import RelayError, RelayErrorCode
from lexigram.contracts.ai.relay.ir import StreamDelta, StreamState
from lexigram.contracts.ai.relay.types import RelayFormat, RelayLoss, RelayUsage
from lexigram.contracts.core.result import Result

__all__ = [
    "StreamEmitter",
    "StreamNormalizer",
    "StreamSession",
    "StreamSnapshot",
    "StreamToolCallRecord",
]


def _pre_text(state: StreamSnapshot, delta: StreamDelta) -> str:
    """Reconstruct the text accumulated before a delta was applied."""
    if delta.kind == "content" and delta.content and state.text.endswith(delta.content):
        return state.text[: -len(delta.content)]
    return state.text


def _pre_thinking(state: StreamSnapshot, delta: StreamDelta) -> str:
    """Reconstruct the thinking text before a delta was applied."""
    if (
        delta.kind == "thinking"
        and delta.thinking_delta
        and state.thinking_text.endswith(delta.thinking_delta)
    ):
        return state.thinking_text[: -len(delta.thinking_delta)]
    return state.thinking_text


def _first_tool_contribution(state: StreamSnapshot, delta: StreamDelta) -> bool:
    """Whether a tool-call delta is the first contribution for its index.

    A tool block/item opens on the first delta that carries any fragment
    for a source-side index.  Later fragments change the accumulated
    record, so equality against the joined record identifies the first.
    """
    index = delta.tool_call_index
    if index is None:
        return False
    record: StreamToolCallRecord | None = None
    for candidate in state.tool_calls:
        if candidate.index == index:
            record = candidate
            break
    if record is None:
        return False
    contributed = (
        delta.tool_call_id is not None
        or delta.tool_call_name is not None
        or delta.tool_call_arguments is not None
    )
    return contributed and (
        record.id == (delta.tool_call_id or "")
        and record.name == (delta.tool_call_name or "")
        and record.arguments == (delta.tool_call_arguments or "")
    )


def _pre_tool_indices(state: StreamSnapshot, delta: StreamDelta) -> set[int]:
    """Tool call indices that existed before a delta was applied."""
    indices = {record.index for record in state.tool_calls}
    if delta.kind == "tool_call" and delta.tool_call_index is not None:
        if _first_tool_contribution(state, delta):
            indices.discard(delta.tool_call_index)
    return indices


def _started_pre(state: StreamSnapshot, delta: StreamDelta) -> bool:
    """Whether the stream had accumulated any state before a delta."""
    if state.role is not None and delta.kind != "role":
        return True
    if _pre_text(state, delta):
        return True
    if _pre_thinking(state, delta):
        return True
    if _pre_tool_indices(state, delta):
        return True
    if state.usage is not None and state.usage is not delta.usage:
        return True
    if state.finish_reason is not None and not (
        delta.kind == "finish" and state.finish_reason == delta.finish_reason
    ):
        return True
    return state.status is not None and not (
        delta.kind == "status" and state.status == delta.status
    )


@runtime_checkable
class StreamNormalizer(Protocol):
    """A source mapper's ``stream_to_delta`` viewed as a callable.

    Maps one source wire event into zero or more canonical
    ``StreamDelta`` objects.  The session hands the current accumulated
    ``StreamState`` so a mapper can ground decisions on prior events.
    """

    def __call__(
        self, event: Any, *, state: StreamState
    ) -> Result[tuple[StreamDelta, ...], RelayError]:
        """Convert one source wire event into canonical deltas."""
        ...


@runtime_checkable
class StreamEmitter(Protocol):
    """A target emitter's ``delta_to_stream`` viewed as a callable.

    Maps one canonical ``StreamDelta`` into zero or more target wire
    events.  The session hands the accumulated :class:`StreamSnapshot`
    so the emitter can stamp metadata and close blocks with full data.
    """

    def __call__(
        self, delta: StreamDelta, *, state: StreamSnapshot
    ) -> Result[tuple[Any, ...], RelayError]:
        """Convert one canonical delta into target wire events."""
        ...


@dataclass(frozen=True)
class StreamToolCallRecord:
    """Accumulated state of one tool call inside a stream session.

    Attributes:
        index: Source-side tool call index (stable across fragments).
        id: Fragmented id, joined verbatim so far.
        name: Fragmented function name, joined verbatim so far.
        arguments: Fragmented JSON argument text, kept raw until the
            stream ends.  Invalid/incomplete JSON is never parsed.
    """

    index: int
    id: str = ""
    name: str = ""
    arguments: str = ""


@dataclass(frozen=True)
class StreamSnapshot:
    """Read-only snapshot of a stream session.

    Attributes:
        source: Upstream wire format.
        target: Downstream wire format.
        model: Model name stamped on emitted chunks.
        stream_id: Upstream stream id, or ``None``.
        created: Epoch seconds the stream started, or ``None``.
        include_usage: Whether a final usage event is requested.
        text: Accumulated assistant text.
        role: Announced assistant role, or ``None``.
        thinking_text: Accumulated thinking/reasoning text.
        thinking_signatures: Thinking signatures taken verbatim, in order.
        tool_calls: Accumulated tool call fragments by source index.
        usage: Latest usage seen (may be the only content of a chunk),
            or ``None``.
        finish_reason: Raw finish reason from a terminal event, or ``None``.
        status: Last target status value, or ``None``.
        open_blocks: Content block indices opened but not yet closed.
        next_output_index: Next target output index to assign.
        is_done: Whether the stream has been finalized.
        warnings: Human-readable loss messages accumulated so far.
        losses: Machine-readable ``RelayLoss`` records accumulated while
            converting streams.
    """

    source: RelayFormat
    target: RelayFormat
    model: str
    stream_id: str | None
    created: int | None
    include_usage: bool
    text: str
    role: str | None
    thinking_text: str
    thinking_signatures: tuple[str, ...]
    tool_calls: tuple[StreamToolCallRecord, ...]
    usage: RelayUsage | None
    finish_reason: str | None
    status: str | None
    open_blocks: tuple[int, ...]
    next_output_index: int
    is_done: bool
    warnings: tuple[str, ...] = ()
    losses: tuple[RelayLoss, ...] = ()


class StreamSession:
    """One upstream stream's mutable conversion state.

    The session buffers fragmented tool calls by source index, preserves
    invalid/incomplete argument JSON verbatim until the stream ends, and
    remembers the latest usage event (including usage-only terminal
    chunks).  Mutable state stays private; callers observe it through
    :meth:`snapshot` and never through the protocol.
    """

    def __init__(
        self,
        *,
        source: RelayFormat,
        target: RelayFormat,
        model: str,
        normalizer: StreamNormalizer,
        emitter: StreamEmitter,
        stream_id: str | None = None,
        created: int | None = None,
        include_usage: bool = False,
    ) -> None:
        self._source = source
        self._target = target
        self._model = model
        self._stream_id = stream_id
        self._created = created
        self._include_usage = include_usage
        self.normalizer = normalizer
        self.emitter = emitter

        self._text = ""
        self._role: str | None = None
        self._thinking_parts: list[str] = []
        self._thinking_signatures: list[str] = []
        self._tool_calls: dict[int, StreamToolCallRecord] = {}
        self._usage: RelayUsage | None = None
        self._finish_reason: str | None = None
        self._status: str | None = None
        self._open_blocks: list[int] = []
        self._next_output_index = 0
        self._finalized = False
        self._warnings: list[str] = []
        self._losses: list[RelayLoss] = []

    def accept(self, event: Any) -> tuple[Any, ...]:
        """Accept one source wire event and emit target events.

        Args:
            event: One source wire event (DTO or raw dict per mapper).

        Returns:
            Zero, one, or many target wire events emitted for this event.

        Raises:
            RelayError: Wrong source format (``stream_state_invalid``),
                already finalized (``stream_already_finalized``), or a
                malformed event.
        """
        if self._finalized:
            raise stream_already_finalized(
                f"cannot accept event on finalized stream {self._stream_id!r}"
            )
        state = self._stream_state()
        result = self.normalizer(event, state=state)
        if result.is_err():
            error = result.unwrap_err()
            if error.code == RelayErrorCode.UNSUPPORTED_FORMAT.value:
                raise stream_state_invalid(str(error))
            raise error
        emitted: list[Any] = []
        for delta in result.unwrap():
            self._apply(delta)
            emission = self.emitter(delta, state=self.snapshot())
            if emission.is_err():
                raise emission.unwrap_err()
            emitted.extend(emission.unwrap())
        return tuple(emitted)

    def finalize(self) -> tuple[Any, ...]:
        """Close the stream deterministically and return terminal events.

        A stream that never saw a terminal event is closed with a safe
        ``finish``/``stop`` delta; a requested usage event is appended
        when usage was observed.  Repeated calls return an empty tuple
        without further mutation.

        Returns:
            Target terminal events; empty when already finalized.
        """
        if self._finalized:
            return ()
        self._finalized = True
        terminal: list[Any] = []
        if self._finish_reason is None:
            safe_stop = StreamDelta(kind="finish", finish_reason="stop")
            self._finish_reason = "stop"
            terminal.extend(self._emit(safe_stop))
        if self._include_usage and self._usage is not None:
            usage_delta = StreamDelta(kind="usage", usage=self._usage)
            terminal.extend(self._emit(usage_delta))
        return tuple(terminal)

    def snapshot(self) -> StreamSnapshot:
        """Return a read-only snapshot of the accumulated session state."""
        return StreamSnapshot(
            source=self._source,
            target=self._target,
            model=self._model,
            stream_id=self._stream_id,
            created=self._created,
            include_usage=self._include_usage,
            text=self._text,
            role=self._role,
            thinking_text=self._thinking_text(),
            thinking_signatures=tuple(self._thinking_signatures),
            tool_calls=tuple(
                self._tool_calls[index] for index in self._tool_call_order()
            ),
            usage=self._usage,
            finish_reason=self._finish_reason,
            status=self._status,
            open_blocks=tuple(self._open_blocks),
            next_output_index=self._next_output_index,
            is_done=self._finalized,
            warnings=tuple(self._warnings),
            losses=tuple(self._losses),
        )

    def _stream_state(self) -> StreamState:
        """Build the immutable mapper-facing state for this call."""
        return StreamState(
            source=self._source,
            target=self._target,
            model=self._model,
            include_usage=self._include_usage,
            tool_calls=[],
            thinking_signatures=list(self._thinking_signatures),
            is_done=self._finalized,
            usage=self._usage,
        )

    def record_loss(
        self, *, field: str, reason: str, severity: str = "warning"
    ) -> None:
        """Record a semantic loss and its rendered warning on the session.

        Emitters call this when the target format cannot represent a
        source feature.  The snapshot exposes the accumulated records and
        warnings; nothing is raised.

        Args:
            field: Source wire field (or feature) that was adapted.
            reason: Machine-readable reason (e.g. ``thinking_not_supported``).
            severity: ``error``, ``warning``, or ``info``.
        """
        loss = RelayLoss(
            field=field, target=self._target, reason=reason, severity=severity
        )
        self._losses.append(loss)
        self._warnings.append(f"{field}: {reason} ({self._target.value}, {severity})")

    def _thinking_text(self) -> str:
        return "".join(self._thinking_parts)

    def _tool_call_order(self) -> list[int]:
        return list(self._tool_calls)

    def _apply(self, delta: StreamDelta) -> None:
        """Fold one canonical delta into the accumulated state."""
        if delta.kind == "content":
            if delta.content:
                self._text += delta.content
            if delta.block_index is not None:
                if delta.block_index not in self._open_blocks:
                    self._open_blocks.append(delta.block_index)
            if delta.output_index is not None:
                self._next_output_index = max(
                    self._next_output_index, delta.output_index + 1
                )
        elif delta.kind == "role":
            if delta.role is not None:
                self._role = delta.role
        elif delta.kind == "thinking":
            if delta.thinking_delta:
                self._thinking_parts.append(delta.thinking_delta)
            signature = delta.passthrough.get("signature")
            if isinstance(signature, str) and signature:
                self._thinking_signatures.append(signature)
        elif delta.kind == "tool_call":
            if delta.tool_call_index is None:
                return
            record = self._tool_calls.setdefault(
                delta.tool_call_index,
                StreamToolCallRecord(index=delta.tool_call_index),
            )
            if delta.tool_call_id:
                record = StreamToolCallRecord(
                    index=record.index,
                    id=record.id + delta.tool_call_id,
                    name=record.name,
                    arguments=record.arguments,
                )
            if delta.tool_call_name:
                record = StreamToolCallRecord(
                    index=record.index,
                    id=record.id,
                    name=record.name + delta.tool_call_name,
                    arguments=record.arguments,
                )
            if delta.tool_call_arguments:
                record = StreamToolCallRecord(
                    index=record.index,
                    id=record.id,
                    name=record.name,
                    arguments=record.arguments + delta.tool_call_arguments,
                )
            self._tool_calls[delta.tool_call_index] = record
        elif delta.kind == "usage":
            if delta.usage is not None:
                self._usage = delta.usage
        elif delta.kind == "finish":
            if delta.finish_reason is not None:
                self._finish_reason = delta.finish_reason
        elif delta.kind == "status":
            if delta.status is not None:
                self._status = delta.status
        if delta.usage is not None:
            self._usage = delta.usage

    def _emit(self, delta: StreamDelta) -> tuple[Any, ...]:
        """Route one delta through the target emitter."""
        emission = self.emitter(delta, state=self.snapshot())
        if emission.is_err():
            raise emission.unwrap_err()
        return tuple(emission.unwrap())
