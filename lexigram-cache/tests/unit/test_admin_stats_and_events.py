"""Focused tests for cache domain events and the admin stats page."""

from __future__ import annotations

from typing import Any

from lexigram.cache.admin.pages.stats import CacheStatsPage
from lexigram.cache.events import (
    CacheConnectedEvent,
    CacheEvictedEvent,
    CacheHitEvent,
    CacheMissEvent,
)
from lexigram.contracts.domain.events import DomainEvent
from lexigram.contracts.core.health import (
    HealthCheckResult,
    HealthStatus,
)


class _FakeCache:
    def __init__(self, health: HealthCheckResult | Exception) -> None:
        self._health = health

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if isinstance(self._health, Exception):
            raise self._health
        return self._health


class TestCacheEvents:
    def test_cache_hit_event(self) -> None:
        event = CacheHitEvent(key="k", backend="memory")
        assert isinstance(event, DomainEvent)
        assert event.key == "k"
        assert event.backend == "memory"

    def test_cache_miss_event(self) -> None:
        event = CacheMissEvent(key="k", backend="memory")
        assert event.key == "k"

    def test_cache_evicted_event(self) -> None:
        event = CacheEvictedEvent(key="k", backend="memory", reason="ttl")
        assert event.reason == "ttl"

    def test_cache_connected_event(self) -> None:
        event = CacheConnectedEvent(backend="redis", host="h")
        assert event.host == "h"


class TestCacheStatsPage:
    def _healthy(self, **details: Any) -> HealthCheckResult:
        return HealthCheckResult(
            component="cache",
            status=HealthStatus.HEALTHY,
            duration_ms=12.5,
            details=details,
        )

    def test_no_cache_returns_unavailable(self) -> None:
        import asyncio

        response = asyncio.run(CacheStatsPage(cache=None).handle(object()))
        assert "Cache Unavailable" in response.body.decode()

    def test_healthy_with_numeric_metrics(self) -> None:
        import asyncio

        cache = _FakeCache(
            self._healthy(
                metrics={
                    "hit_rate": 0.8,
                    "total_operations": 10,
                    "hits": 8,
                    "misses": 2,
                    "sets": 1,
                    "deletes": 0,
                    "errors": 0,
                    "avg_latency_ms": 3.2,
                }
            )
        )
        html = asyncio.run(CacheStatsPage(cache=cache).handle(object())).body.decode()
        assert "Cache Statistics" in html
        assert "OK" in html
        assert "80%" in html
        assert "3.2ms" in html
        assert "Backend Details" in html
        assert "_FakeCache" in html

    def test_healthy_with_string_metrics(self) -> None:
        import asyncio

        cache = _FakeCache(
            self._healthy(metrics={"hit_rate": "N/A", "avg_latency_ms": "unknown"})
        )
        html = asyncio.run(CacheStatsPage(cache=cache).handle(object())).body.decode()
        assert "N/A" in html
        assert "unknown" in html

    def test_health_check_raises_marks_down(self) -> None:
        import asyncio

        cache = _FakeCache(RuntimeError("boom"))
        html = asyncio.run(CacheStatsPage(cache=cache).handle(object())).body.decode()
        assert "Down" in html
        assert "Unhealthy" in html