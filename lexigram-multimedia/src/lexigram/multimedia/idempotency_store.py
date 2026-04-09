"""Fallback IdempotencyStoreProtocol implementation.

Used only when no IdempotencyStoreProtocol (e.g. from lexigram-resilience)
is bound in the container. lexigram-multimedia does not take a hard
dependency on lexigram-resilience just for this — that isn't one of the
framework's confirmed package-boundary exceptions — so it carries a small
private fallback instead. Returns raw values, not Result-wrapped, matching
lexigram-resilience's InMemoryIdempotencyStore — IdempotencyManager.check_duplicate()
already handles both shapes defensively.
"""

from __future__ import annotations

from typing import Any


class InMemoryIdempotencyStoreFallback:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        return self._data.get(key)

    async def get_record(self, key: str) -> Any | None:
        return self._data.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        self._data[key] = value

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def acquire(self, key: str, ttl: int | None = None) -> bool:
        if key in self._data:
            return False
        self._data[key] = True
        return True


__all__ = ["InMemoryIdempotencyStoreFallback"]
