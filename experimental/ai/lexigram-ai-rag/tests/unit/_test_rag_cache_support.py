"""Shared fixtures/stubs for test_rag_cache tests."""

from __future__ import annotations

from typing import Any


class MockCacheBackend:
    def __init__(self):
        self._data = {}

    async def get(self, key: str) -> Any | None:
        return self._data.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        self._data[key] = value
        return True

    async def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    async def invalidate_pattern(self, pattern: str) -> int:
        count = 0
        keys_to_delete = []
        for k in self._data:
            if pattern in k:
                keys_to_delete.append(k)
        for k in keys_to_delete:
            del self._data[k]
            count += 1
        return count

    async def clear(self) -> bool:
        self._data.clear()
        return True
