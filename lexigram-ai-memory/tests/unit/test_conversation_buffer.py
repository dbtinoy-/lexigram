"""Unit tests for ConversationBuffer working memory strategy."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from lexigram.ai.memory.working.conversation_buffer import ConversationBuffer
from lexigram.contracts.ai.memory import MemoryEntry


def _make_entry(content: str) -> MemoryEntry:
    return MemoryEntry(
        id=str(uuid4()),
        content=content,
        role="user",
        timestamp=datetime.now(UTC),
    )


class TestConversationBuffer:
    async def test_add_within_limits(self) -> None:
        buffer = ConversationBuffer(max_turns=10, max_tokens=100)
        e1 = _make_entry("hello")
        e2 = _make_entry("world")
        
        await buffer.add(e1)
        await buffer.add(e2)
        
        ctx = buffer.get_context()
        assert len(ctx) == 2
        assert ctx[0] == e1
        assert ctx[1] == e2
        assert buffer.size == 2
        assert buffer.total_tokens > 0

    async def test_evict_max_turns(self) -> None:
        buffer = ConversationBuffer(max_turns=3, max_tokens=100)
        
        entries = [_make_entry(f"msg {i}") for i in range(5)]
        for e in entries:
            await buffer.add(e)
            
        ctx = buffer.get_context()
        assert len(ctx) == 3
        # Should keep the last 3 entries
        assert ctx == entries[-3:]

    async def test_evict_max_tokens(self) -> None:
        buffer = ConversationBuffer(max_turns=10, max_tokens=10) # ~40 chars max
        
        await buffer.add(_make_entry("Hello World This Is A Long Message")) # ~9 tokens
        await buffer.add(_make_entry("Short")) # ~1 token
        
        # Adding this should trigger eviction of the first message
        await buffer.add(_make_entry("Another long one pushes out the first"))
        
        ctx = buffer.get_context()
        assert len(ctx) < 3
        # The first long message should definitely be gone
        assert not any("Hello World" in e.content for e in ctx)

    async def test_never_evict_last_message(self) -> None:
        buffer = ConversationBuffer(max_turns=10, max_tokens=2) # Extremely small token limit
        
        large_entry = _make_entry("x" * 100) # ~25 tokens, far exceeds the limit
        await buffer.add(large_entry)
        
        ctx = buffer.get_context()
        assert len(ctx) == 1
        assert ctx[0] == large_entry
        # Eviction stops when length is 1, so the huge message stays

    def test_clear(self) -> None:
        buffer = ConversationBuffer(max_turns=10, max_tokens=10)
        import asyncio
        asyncio.run(buffer.add(_make_entry("test")))
        assert buffer.size == 1
        
        buffer.clear()
        assert buffer.size == 0
        assert buffer.total_tokens == 0
        assert len(buffer.get_context()) == 0
