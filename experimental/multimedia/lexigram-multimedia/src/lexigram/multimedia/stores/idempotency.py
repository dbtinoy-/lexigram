"""Fallback IdempotencyStoreProtocol implementation.

Used only when no IdempotencyStoreProtocol (e.g. from lexigram-resilience)
is bound in the container. lexigram-multimedia does not take a hard
dependency on lexigram-resilience just for this — that isn't one of the
framework's confirmed package-boundary exceptions — so it carries a small
private fallback instead. Returns raw values, not Result-wrapped, matching
lexigram-resilience's InMemoryIdempotencyStore — IdempotencyManager.check_duplicate()
already handles both shapes defensively.

TTL semantics mirror lexigram-resilience's in-memory store: entries carry a
monotonic-clock expiry and are treated as absent once expired, so idempotency
windows close and the dict does not grow without bound.
"""

from __future__ import annotations

from typing import Any

from lexigram.primitives import clock as ambient_clock


class InMemoryIdempotencyStoreFallback:
    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, float | None]] = {}

    def _expired(self, entry: tuple[Any, float | None]) -> bool:
        _, expires_at = entry
        return expires_at is not None and ambient_clock.monotonic() > expires_at

    async def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        if self._expired(entry):
            del self._data[key]
            return None
        return entry[0]

    async def get_record(self, key: str) -> Any | None:
        return await self.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expires_at = ambient_clock.monotonic() + ttl if ttl is not None else None
        self._data[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def acquire(self, key: str, ttl: int | None = None) -> bool:
        entry = self._data.get(key)
        if entry is not None and not self._expired(entry):
            return False
        expires_at = ambient_clock.monotonic() + ttl if ttl is not None else None
        self._data[key] = (True, expires_at)
        return True


__all__ = ["InMemoryIdempotencyStoreFallback"]
