"""In-memory governance persistence backend.

Process-local governance persistence using plain Python dicts.  Request
counts are tracked with a sliding-window approach (list of monotonic
timestamps).  Spend totals are stored as plain floats.

This implementation is **not** suitable for multi-process or multi-replica
deployments.  Use
:class:`~lexigram.ai.governance.persistence.RedisGovernancePersistence`
in production.
"""

from __future__ import annotations

import time


class InMemoryGovernancePersistence:
    """Process-local governance persistence using plain Python dicts.

    Request counts are tracked with a sliding-window approach (list of
    monotonic timestamps).  Spend totals are stored as plain floats.

    This implementation is **not** suitable for multi-process or
    multi-replica deployments.  Use :class:`RedisGovernancePersistence`
    in production.
    """

    def __init__(self) -> None:
        self._request_buckets: dict[str, list[float]] = {}
        self._spend_totals: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._calendar: dict[str, list[tuple[float, float]]] = {}

    async def incr_requests(self, key: str, window: float) -> int:
        now = time.monotonic()
        bucket = self._request_buckets.setdefault(key, [])
        # Prune entries outside the window, then record current request
        self._request_buckets[key] = [t for t in bucket if now - t <= window]
        self._request_buckets[key].append(now)
        return len(self._request_buckets[key])

    async def add_spend(self, key: str, amount: float, ttl: int) -> float:
        current = self._spend_totals.get(key, 0.0)
        updated = current + amount
        self._spend_totals[key] = updated
        return updated

    async def get_spend(self, key: str) -> float:
        return self._spend_totals.get(key, 0.0)

    async def read_gauge(self, key: str) -> float:
        return self._gauges.get(key, 0.0)

    async def write_gauge(self, key: str, value: float, ttl: int) -> None:
        self._gauges[key] = value

    async def incr_gauge(self, key: str, delta: float, ttl: int) -> float:
        current = self._gauges.get(key, 0.0)
        updated = max(current + delta, 0.0)
        self._gauges[key] = updated
        return updated

    async def add_calendar_entry(self, key: str, timestamp: float, ttl: int) -> None:
        now = time.monotonic()
        bucket = self._calendar.setdefault(key, [])
        bucket.append((now, timestamp))

    async def query_calendar(self, key: str, start: float, end: float) -> list[float]:
        results = []
        bucket = self._calendar.get(key, [])
        for _, ts in bucket:
            if start <= ts <= end:
                results.append(ts)
        return results


__all__ = ["InMemoryGovernancePersistence"]
