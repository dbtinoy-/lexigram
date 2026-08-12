"""Stream conversion for the Claude mapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.relay.errors import unsupported_feature
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.ir import StreamDelta, StreamState
from lexigram.contracts.core.result import Err, Result

if TYPE_CHECKING:
    from lexigram.ai.relay.mappers.claude import ClaudeMapper


class StreamMixin:
    """Stream conversion is deferred to the shared stream lifecycle task."""

    def stream_to_delta(
        self: ClaudeMapper, event: Any, *, state: StreamState
    ) -> Result[tuple[StreamDelta, ...], RelayError]:
        """Stream conversion is deferred to the shared stream lifecycle task."""
        return Err(
            unsupported_feature("claude stream conversion is not implemented yet")
        )

    def delta_to_stream(
        self: ClaudeMapper, delta: StreamDelta, *, state: StreamState
    ) -> Result[tuple[Any, ...], RelayError]:
        """Stream conversion is deferred to the shared stream lifecycle task."""
        return Err(
            unsupported_feature("claude stream conversion is not implemented yet")
        )
