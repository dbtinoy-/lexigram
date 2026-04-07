"""Frozen view models for lexigram-cache admin widgets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HitMissRatioViewModel:
    """View data for cache hit/miss ratio widget."""

    hits: int
    misses: int
    hit_rate_pct: float
    window_minutes: int


@dataclass(frozen=True)
class EvictionRateViewModel:
    """View data for cache eviction rate widget."""

    evictions_per_second: float
    total_evictions: int


@dataclass(frozen=True)
class BackendPingViewModel:
    """View data for cache backend ping widget."""

    latency_ms: float
    is_reachable: bool
    backend_name: str


__all__ = [
    "BackendPingViewModel",
    "EvictionRateViewModel",
    "HitMissRatioViewModel",
]
