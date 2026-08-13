"""Anthropic Claude Messages request and response mapper.

Converts the Claude Messages wire DTOs
(:class:`ClaudeRequest` / :class:`ClaudeResponse`) into the canonical
relay IR and back.  Stream conversion is handled by the shared stream
lifecycle task and reports ``unsupported_feature`` until then.
"""

from __future__ import annotations

from lexigram.ai.relay.mappers.claude.request import RequestMixin
from lexigram.ai.relay.mappers.claude.response import ResponseMixin
from lexigram.ai.relay.mappers.claude.stream import StreamMixin
from lexigram.ai.relay.mappers.claude.utils import _TARGET

__all__ = ["ClaudeMapper"]


class ClaudeMapper(RequestMixin, ResponseMixin, StreamMixin):
    """Bidirectional Anthropic Claude Messages converter.

    Attributes:
        format: The wire format this mapper handles.
    """

    format = _TARGET
