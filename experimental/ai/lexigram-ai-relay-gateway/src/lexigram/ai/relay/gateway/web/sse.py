"""SSE framing from normalized relay events into client wire protocols.

``RelayWireEvent`` values are framed as Server-Sent Events following the
client's inbound wire protocol: OpenAI Chat streams data-only frames with
a ``[DONE]`` terminator, OpenAI Responses and Claude streams carry
``event:`` names above the data line, and Gemini streams data-only frames
without a terminator.  JSON serialization goes through
``lexigram.serialization`` only.
"""

from __future__ import annotations

from lexigram.contracts.ai.relay import RelayFormat, RelayWireEvent
from lexigram.serialization import dumps_str

__all__ = ["SSEEncoder"]


class SSEEncoder:
    """Frame ``RelayWireEvent`` values as SSE for one client protocol.

    Encoders are stateless; a single instance can frame an entire stream.
    Each ``encode`` call returns the complete bytes for one event,
    including any ``[DONE]`` terminator, so streams never need module or
    instance-level buffering.
    """

    def __init__(self, source: RelayFormat) -> None:
        """Bind the encoder to the client's wire protocol.

        Args:
            source: The client's relay format; frames follow its syntax.
        """
        self._source = source

    def encode(self, event: RelayWireEvent) -> bytes:
        """Encode one event as a complete SSE frame.

        Args:
            event: The normalized wire event to frame.

        Returns:
            The full SSE frame bytes for the event, including the
            trailing blank line and any ``[DONE]`` terminator.
        """
        data = dumps_str(event.data).encode("utf-8") if event.data is not None else b""
        if self._source == RelayFormat.OPENAI_CHAT:
            if event.terminal and data:
                return b"data: " + data + b"\n\ndata: [DONE]\n\n"
            if event.terminal:
                return b"data: [DONE]\n\n"
            return b"data: " + data + b"\n\n"
        if self._source in {RelayFormat.OPENAI_RESPONSES, RelayFormat.CLAUDE}:
            name = self._event_name(event)
            return b"event: " + name.encode("utf-8") + b"\ndata: " + data + b"\n\n"
        return b"data: " + data + b"\n\n"

    def encode_terminal(
        self, source: RelayFormat, terminal_event: RelayWireEvent | None
    ) -> bytes:
        """Emit the closing frame when the client protocol requires one.

        OpenAI Chat streams terminate with ``data: [DONE]``.  When the
        terminal event already passed through ``encode`` (which appends
        ``[DONE]`` for terminal events) nothing more is emitted; a stream
        that ends without a terminal event gets the ``[DONE]`` frame here
        so the client always sees exactly one terminator.  All other
        formats terminate in-band and return nothing.

        Args:
            source: The client's relay format.
            terminal_event: The framed terminal event, if any.

        Returns:
            The closing frame, or ``b""`` when none is needed.
        """
        if source != RelayFormat.OPENAI_CHAT:
            return b""
        if terminal_event is not None:
            return b""
        return b"data: [DONE]\n\n"

    def _event_name(self, event: RelayWireEvent) -> str:
        """Derive the SSE event name from the event or its data type."""
        name = event.event
        if name is None:
            fallback = (
                event.data.get("type", "message")
                if event.data is not None
                else "message"
            )
            name = fallback if isinstance(fallback, str) else str(fallback)
        return name
