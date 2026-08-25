"""Protocol plumbing tests for the stream session.

Verifies that emitters receive the accumulated tool-call snapshot
rather than raw fragments.
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.ir import StreamDelta
from lexigram.contracts.ai.relay.types import RelayFormat
from lexigram.contracts.core.result import Ok, Result

from ._stream_emitters_support import make_session, run


def test_emitter_receives_accumulated_snapshot() -> None:
    """Emitters see the joined tool-call record, not fragments."""
    session, normalizer = make_session(RelayFormat.OPENAI_CHAT, RelayFormat.OPENAI_CHAT)
    captured: list[Any] = []

    def recorder(
        delta: StreamDelta, *, state: Any
    ) -> Result[tuple[Any, ...], RelayError]:
        captured.append(state)
        return Ok((delta,))

    session.emitter = recorder  # type: ignore[assignment]
    run(
        session,
        [
            ("tool", 0, "call_", None, None),
            ("tool", 0, None, "get_w", None),
            ("tool", 0, None, None, '{"a":1}'),
        ],
    )
    assert normalizer.calls
    assert len(captured) == 3
    last = captured[-1]
    assert last.tool_calls[0].id == "call_"
    assert last.tool_calls[0].name == "get_w"
    assert last.tool_calls[0].arguments == '{"a":1}'
