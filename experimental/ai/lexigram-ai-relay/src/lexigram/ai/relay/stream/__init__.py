"""Stream session state and shared lifecycle rules.

The session state machine ties a source mapper's ``stream_to_delta`` to
a target mapper's ``delta_to_stream``.  Mutable state stays private to
:class:`StreamSession`; callers observe it through read-only snapshots.
The bundled emitters map canonical deltas into the four target wire
event families.
"""

from __future__ import annotations

from lexigram.ai.relay.stream.claude import claude_emitter
from lexigram.ai.relay.stream.gemini import gemini_emitter
from lexigram.ai.relay.stream.openai_chat import openai_chat_emitter
from lexigram.ai.relay.stream.openai_responses import openai_responses_emitter
from lexigram.ai.relay.stream.state import (
    StreamEmitter,
    StreamNormalizer,
    StreamSession,
    StreamSnapshot,
    StreamToolCallRecord,
)

__all__ = [
    "StreamEmitter",
    "StreamNormalizer",
    "StreamSession",
    "StreamSnapshot",
    "StreamToolCallRecord",
    "claude_emitter",
    "gemini_emitter",
    "openai_chat_emitter",
    "openai_responses_emitter",
]
