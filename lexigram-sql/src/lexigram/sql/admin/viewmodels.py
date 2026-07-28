"""Frozen view models for lexigram-sql admin widgets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PoolUtilizationViewModel:
    """View data for the database connection pool widget."""

    pool_size: int
    active_connections: int
    idle_connections: int
    utilization_pct: float


@dataclass(frozen=True)
class QueryStatsViewModel:
    """View data for the query statistics widget."""

    total_queries: int
    avg_duration_ms: float
    slow_queries: int
    error_count: int


@dataclass(frozen=True)
class MigrationStatusViewModel:
    """View data for the migration status widget."""

    current_version: str
    total_applied: int
    pending_count: int
    is_current: bool


__all__ = [
    "MigrationStatusViewModel",
    "PoolUtilizationViewModel",
    "QueryStatsViewModel",
]
