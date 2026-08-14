"""Tests for HTMX SSE (Server-Sent Events) support."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from lexigram.ui.htmx.sse import SSEMessage, SSEStream


class TestSSEMessage:
    """Tests for SSEMessage class."""

    def test_sse_message_basic_data(self) -> None:
        """Test basic SSE message with string data."""
        msg = SSEMessage("Hello, World!")
        result = str(msg)
        assert "data: Hello, World!" in result
        assert result.endswith("\n\n")

    def test_sse_message_with_event(self) -> None:
        """Test SSE message with event type."""
        msg = SSEMessage("update", event="progress")
        result = str(msg)
        assert "event: progress" in result
        assert "data: update" in result

    def test_sse_message_with_event_id(self) -> None:
        """Test SSE message with event ID."""
        msg = SSEMessage("message", event_id="msg-123")
        result = str(msg)
        assert "id: msg-123" in result
        assert "data: message" in result

    def test_sse_message_with_retry(self) -> None:
        """Test SSE message with retry interval."""
        msg = SSEMessage("reconnect", retry=5000)
        result = str(msg)
        assert "retry: 5000" in result
        assert "data: reconnect" in result

    def test_sse_message_with_dict_data(self) -> None:
        """Test SSE message with dict data (JSON serialized)."""
        msg = SSEMessage({"status": "ok", "count": 5})
        result = str(msg)
        assert "data:" in result
        assert "status" in result
        assert "ok" in result

    def test_sse_message_multiline_data(self) -> None:
        """Test SSE message with multiline data."""
        msg = SSEMessage("line1\nline2\nline3")
        result = str(msg)
        assert result.count("data:") == 3

    def test_sse_message_all_options(self) -> None:
        """Test SSE message with all options."""
        msg = SSEMessage("complete", event="finish", event_id="evt-1", retry=3000)
        result = str(msg)
        assert "id: evt-1" in result
        assert "event: finish" in result
        assert "retry: 3000" in result
        assert "data: complete" in result


class TestSSEStream:
    """Tests for SSEStream class."""

    @pytest.mark.asyncio
    async def test_sse_stream_generator_basic(self) -> None:
        """Test SSEStream with basic generator."""
        async def generator() -> AsyncGenerator[SSEMessage, None]:
            yield SSEMessage("message 1")
            yield SSEMessage("message 2")

        stream = SSEStream(generator())
        assert stream.media_type == "text/event-stream"
        assert stream.headers["Cache-Control"] == "no-cache"
        assert stream.headers["Connection"] == "keep-alive"
        assert stream.headers["X-Accel-Buffering"] == "no"

    @pytest.mark.asyncio
    async def test_sse_stream_with_custom_headers(self) -> None:
        """Test SSEStream with custom headers."""
        async def generator() -> AsyncGenerator[SSEMessage, None]:
            yield SSEMessage("data")

        stream = SSEStream(generator(), status_code=201)
        assert stream.status_code == 201


class TestSSEStreamContent:
    """Tests for SSEStream content generation."""

    @pytest.mark.asyncio
    async def test_sse_stream_yields_messages(self) -> None:
        """Test that stream yields all messages."""
        messages = []

        async def generator() -> AsyncGenerator[SSEMessage, None]:
            yield SSEMessage("first")
            yield SSEMessage("second")
            yield SSEMessage("third")

        stream = SSEStream(generator())

        async def collect_content():
            async for chunk in stream.body_iterator:
                messages.append(chunk)

        await collect_content()

        combined = "".join(messages)
        assert "data: first" in combined
        assert "data: second" in combined
        assert "data: third" in combined

    @pytest.mark.asyncio
    async def test_sse_stream_empty_generator(self) -> None:
        """Test SSEStream with empty generator."""
        async def generator() -> AsyncGenerator[SSEMessage, None]:
            return
            yield  # type: ignore[unreachable]

        stream = SSEStream(generator())
        content = b"".join([chunk async for chunk in stream.body_iterator])
        assert content == b""


class TestSSEEdgeCases:
    """Tests for edge cases in SSE handling."""

    def test_sse_message_empty_string_data(self) -> None:
        """Test SSE message with empty string data."""
        msg = SSEMessage("")
        result = str(msg)
        assert "data: " in result

    def test_sse_message_none_data(self) -> None:
        """Test SSE message with None data."""
        msg = SSEMessage(None)  # type: ignore[arg-type]
        result = str(msg)
        assert "data: null" in result or "data:" in result

    def test_sse_message_numeric_data(self) -> None:
        """Test SSE message with numeric data."""
        msg = SSEMessage(42)
        result = str(msg)
        assert "data: 42" in result

    def test_sse_message_list_data(self) -> None:
        """Test SSE message with list data."""
        msg = SSEMessage([1, 2, 3])
        result = str(msg)
        assert "data:" in result
        assert "1" in result
        assert "2" in result
        assert "3" in result


class TestSSEFormatCompliance:
    """Tests for SSE format compliance."""

    def test_sse_format_double_newline_terminator(self) -> None:
        """Test SSE messages end with double newline."""
        msg = SSEMessage("test")
        result = str(msg)
        assert result.endswith("\n\n")

    def test_sse_format_data_prefix(self) -> None:
        """Test SSE data lines are properly prefixed."""
        msg = SSEMessage("hello")
        result = str(msg)
        lines = result.strip().split("\n")
        assert lines[0].startswith("data:")

    def test_sse_format_field_order(self) -> None:
        """Test SSE fields follow proper order (id, event, retry, data)."""
        msg = SSEMessage("payload", event="update", event_id="123", retry=1000)
        result = str(msg)
        lines = result.strip().split("\n")
        assert lines[0] == "id: 123"
        assert lines[1] == "event: update"
        assert lines[2] == "retry: 1000"
        assert lines[3] == "data: payload"


def test_sse_region_is_live() -> None:
    """SSE stream regions must announce updates (aria-live)."""
    from lexigram.ui.htmx.sse import SSE

    html = str(SSE(url="/events", target="#main"))
    assert 'aria-live="polite"' in html
    assert 'role="status"' in html
