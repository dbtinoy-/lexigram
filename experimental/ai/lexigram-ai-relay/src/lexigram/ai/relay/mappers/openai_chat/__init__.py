"""OpenAI Chat Completions mapper package.

Public API: :class:`OpenAIChatMapper`. Implementation is split by
conversion direction across :mod:`mapper` (public class composing the
mixins), :mod:`wire_to_ir`, :mod:`ir_to_wire`, and :mod:`_helpers`.
"""

from __future__ import annotations

from lexigram.ai.relay.mappers.openai_chat.mapper import OpenAIChatMapper

__all__ = ["OpenAIChatMapper"]
