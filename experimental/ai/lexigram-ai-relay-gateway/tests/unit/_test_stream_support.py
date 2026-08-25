"""Shared doubles and builders for the relay gateway streaming tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from lexigram.ai.relay.gateway.stream import UpstreamEventParser
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay import (
    RelayFormat,
    UpstreamChunk,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.serialization import dumps

OPENAI_CHAT_1: dict[str, Any] = {
    "id": "chatcmpl-1",
    "object": "chat.completion.chunk",
    "created": 0,
    "model": "gpt-x",
    "choices": [{"index": 0, "delta": {"content": "hi"}, "finish_reason": None}],
}

OPENAI_CHAT_2: dict[str, Any] = {
    "id": "chatcmpl-1",
    "object": "chat.completion.chunk",
    "created": 0,
    "model": "gpt-x",
    "choices": [{"index": 0, "delta": {"content": "bye"}, "finish_reason": None}],
}


class FakeSession:
    """Minimal ``RelayStreamSessionProtocol`` double for stream tests.

    Records every accepted event and finalize call. ``accept_result``
    defaults to echoing the accepted event so relayed DTOs reach the
    wire; ``accept_error`` and ``finalize_result`` override the behavior.
    """

    def __init__(
        self,
        accept_result: tuple[Any, ...] | None = None,
        accept_error: RelayError | None = None,
        finalize_result: tuple[Any, ...] = (),
    ) -> None:
        self.accepted: list[Any] = []
        self.accept_result = accept_result
        self.accept_error = accept_error
        self.finalize_result = finalize_result
        self.finalize_calls = 0

    def accept(self, event: Any) -> tuple[Any, ...]:
        """Record the event and return the configured result."""
        self.accepted.append(event)
        if self.accept_error is not None:
            raise self.accept_error
        if self.accept_result is not None:
            return self.accept_result
        return (event,)

    def finalize(self) -> tuple[Any, ...]:
        """Record the call and return the configured result."""
        self.finalize_calls += 1
        return self.finalize_result

    def snapshot(self) -> Any:
        """Return ``None``; state is read through ``accepted``."""
        return None


class FakeUpstream:
    """Minimal ``RelayUpstreamProtocol`` double for the streaming tests.

    ``stream()`` yields each canned chunk (recording reads) or raises the
    configured error on the first read; ``cancel()`` records calls.
    ``request()`` is unused by the streaming path.
    """

    def __init__(
        self,
        chunks: list[UpstreamChunk] | None = None,
        stream_error: Exception | None = None,
    ) -> None:
        self.chunks = chunks if chunks is not None else []
        self.stream_error = stream_error
        self.reads: list[UpstreamChunk] = []
        self.calls: list[str] = []

    async def stream(self, request: UpstreamRequest) -> AsyncIterator[UpstreamChunk]:
        """Yield the canned chunks, recording each read, or raise."""
        if self.stream_error is not None:
            raise self.stream_error
        for item in self.chunks:
            self.reads.append(item)
            yield item

    async def cancel(self, request_id: str) -> None:
        """Record the cancel call."""
        self.calls.append("cancel")

    async def request(self, request: UpstreamRequest) -> UpstreamResponse:
        """Unused stub; the streaming tests never call it."""
        raise AssertionError("FakeUpstream.request is not used by streaming tests")


def chunk(data: str, event: str | None = None, terminal: bool = False) -> UpstreamChunk:
    """Build an ``UpstreamChunk`` with the given frame fields."""
    return UpstreamChunk(event=event, data=data, terminal=terminal)


def wire(data: dict[str, Any]) -> str:
    """Serialize a wire dict to a JSON string."""
    return dumps(data).decode("utf-8")


def make_request() -> UpstreamRequest:
    """Build an ``UpstreamRequest`` with streaming-test defaults."""
    return UpstreamRequest(
        request_id="req-1",
        method="POST",
        url="https://upstream/v1/chat/completions",
        headers={},
        payload={"model": "gpt-x"},
        timeout_seconds=60.0,
    )


def make_parser(
    session: FakeSession, source: RelayFormat = RelayFormat.OPENAI_CHAT
) -> UpstreamEventParser:
    """Build a parser over the given fake session."""
    return UpstreamEventParser(session=session, source=source, request_id="req-1")
