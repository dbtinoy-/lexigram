"""Fail-closed scope tests for ConversationMemoryStore (F3)."""

from __future__ import annotations

import pytest

from lexigram.ai.memory.stores.conversation import ConversationMemoryStore
from lexigram.contracts.ai.memory import MemoryQuery

from helpers import make_entry


class TestConversationMemoryMissingScope:
    @pytest.mark.asyncio
    async def test_retrieve_without_session_scope_returns_empty(self) -> None:
        store = ConversationMemoryStore()
        await store.store(make_entry("s1 turn", metadata={"session_id": "s1"}))

        results = await store.retrieve(MemoryQuery(owner_id="o", query="x"))

        assert results == []

    @pytest.mark.asyncio
    async def test_retrieve_with_session_scope_returns_only_that_session(
        self,
    ) -> None:
        store = ConversationMemoryStore()
        await store.store(make_entry("s1 turn", metadata={"session_id": "s1"}))
        await store.store(make_entry("s2 turn", metadata={"session_id": "s2"}))

        results = await store.retrieve(
            MemoryQuery(owner_id="o", query="x", filters={"session_id": "s1"})
        )

        assert len(results) == 1
        assert results[0].entry.metadata["session_id"] == "s1"

    @pytest.mark.asyncio
    async def test_get_recent_scoped_to_session(self) -> None:
        store = ConversationMemoryStore()
        await store.store(make_entry("s1 turn", metadata={"session_id": "s1"}))
        await store.store(make_entry("s2 turn", metadata={"session_id": "s2"}))

        recent = await store.get_recent(10, "s1")

        assert [e.metadata["session_id"] for e in recent] == ["s1"]

    @pytest.mark.asyncio
    async def test_store_without_session_scope_stores_nothing(self) -> None:
        store = ConversationMemoryStore()
        await store.store(make_entry("unscoped"))

        assert await store.get_session_entries("_default") == []
        assert await store.get_recent(10, "_default") == []