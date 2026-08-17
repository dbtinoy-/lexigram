"""Stream conversion stubs for the OpenAI Responses mapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.relay.errors import unsupported_feature
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.ir import StreamDelta, StreamState
from lexigram.contracts.core.result import Err, Result

if TYPE_CHECKING:
    from lexigram.ai.relay.mappers.openai_responses import OpenAIResponsesMapper


class StreamMixin:
    """Stream conversion for the OpenAI Responses format.

    Stream conversion is deferred to the shared stream lifecycle task and
    reports ``unsupported_feature`` until then.
    """

    def stream_to_delta(
        self: OpenAIResponsesMapper,
        event: Any,
        *,
        state: StreamState,
    ) -> Result[tuple[StreamDelta, ...], RelayError]:
        """Stream conversion is deferred to the shared stream lifecycle task."""
        return Err(
            unsupported_feature(
                "openai_responses stream conversion is not implemented yet"
            )
        )

    def delta_to_stream(
        self: OpenAIResponsesMapper,
        delta: StreamDelta,
        *,
        state: StreamState,
    ) -> Result[tuple[Any, ...], RelayError]:
        """Stream emission is deferred to the shared stream lifecycle task."""
        return Err(
            unsupported_feature(
                "openai_responses stream conversion is not implemented yet"
            )
        )
