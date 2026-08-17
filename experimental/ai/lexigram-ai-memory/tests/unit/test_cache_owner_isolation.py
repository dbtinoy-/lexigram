"""Cross-owner isolation tests for CacheMemoryBackend.

Uses a test-local fake CacheBackendProtocol that records every key
access so tests can assert keys are namespaced by owner and that one
owner's operations never touch another's keys.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.memory.backends.cache import CacheMemoryBackend
from lexigram.contracts.ai.memory import MemoryQuery
from lexigram.result import Ok

from helpers import make_entry


class _FakeCache:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self.accessed: list[str] = []

    async def get(self, key: str) -> Any:
        self.accessed.append(key)
        return Ok(self._data.get(key))

    async def set(self, key: str, value: str, ttl: int | None = None) -> Any:
        self._data[key] = value
        return Ok(None)

    async def delete(self, key: str) -> Any:
        self._data.pop(key, None)
        return Ok(None)

    async def health_check(self, timeout: float = 5.0) -> Any:
        return Ok(None)


class TestCacheMemoryBackendOwnerIsolation:
    def setup_method(self) -> None:
        self.cache = _FakeCache()
        self.backend = CacheMemoryBackend(self.cache)

    @pytest.mark.asyncio
    async def test_keys_are_namespaced_by_owner(self) -> None:
        await self.backend.store(make_entry("a1", owner_id="A"))
        await self.backend.store(make_entry("b1", owner_id="B"))

        memory_keys = [k for k in self.cache._data if k.startswith("mem:A:")]
        assert len(memory_keys) == 1
        assert any(k.startswith("mem:B:") for k in self.cache._data)
        assert "mem:index:A" in self.cache._data
        assert "mem:index:B" in self.cache._data

    @pytest.mark.asyncio
    async def test_retrieve_scoped_to_owner(self) -> None:
        await self.backend.store(make_entry("a1", owner_id="A"))
        await self.backend.store(make_entry("b1", owner_id="B"))

        results = await self.backend.retrieve(MemoryQuery(owner_id="B", query="x"))

        assert len(results) == 1
        assert results[0].entry.owner_id == "B"

    @pytest.mark.asyncio
    async def test_get_recent_scoped_to_owner(self) -> None:
        await self.backend.store(make_entry("a1", owner_id="A"))
        await self.backend.store(make_entry("b1", owner_id="B"))

        recent = await self.backend.get_recent(10, "A")

        assert [e.owner_id for e in recent] == ["A"]

    @pytest.mark.asyncio
    async def test_delete_scoped_to_owner(self) -> None:
        a_entry = make_entry("a1", owner_id="A")
        await self.backend.store(a_entry)
        await self.backend.store(make_entry("b1", owner_id="B"))

        await self.backend.delete(a_entry.id, "A")

        assert len(await self.backend.get_recent(10, "A")) == 0
        assert len(await self.backend.get_recent(10, "B")) == 1

    @pytest.mark.asyncio
    async def test_clear_touches_only_owner_keys(self) -> None:
        await self.backend.store(make_entry("a1", owner_id="A"))
        await self.backend.store(make_entry("b1", owner_id="B"))
        accessed_before = set(self.cache.accessed)

        await self.backend.clear("A")

        accessed_during = set(self.cache.accessed) - accessed_before
        assert not any("mem:B" in key for key in accessed_during)
        assert len(await self.backend.get_recent(10, "A")) == 0
        assert len(await self.backend.get_recent(10, "B")) == 1