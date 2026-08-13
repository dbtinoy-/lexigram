"""Relay job registry tests (Plan N, Tasks 0 and 1).

Verifies record storage and TTL-based lazy eviction of
``RelayJobRegistry`` with an injectable clock, plus the
``job_ttl_seconds`` configuration default and validation on
``RelayGatewayConfig``.
"""

from __future__ import annotations

import pytest

from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.job_registry import RelayJobRecord, RelayJobRegistry

CHANNEL_NAME = "video-a"
UPSTREAM_JOB_ID = "video-42"
ENDPOINT_KIND = "video_generation"


def make_record(created_at: float = 0.0) -> RelayJobRecord:
    """Build a job record stamped at the given monotonic time."""
    return RelayJobRecord(
        channel_name=CHANNEL_NAME,
        upstream_job_id=UPSTREAM_JOB_ID,
        endpoint_kind=ENDPOINT_KIND,
        submitted_by="tenant-1",
        created_at=created_at,
    )


class FakeClock:
    """Monotonic clock double whose value tests advance explicitly."""

    def __init__(self, now: float = 0.0) -> None:
        self._now = now

    def __call__(self) -> float:
        """Return the configured monotonic time."""
        return self._now

    def advance(self, seconds: float) -> None:
        """Advance the fake time by *seconds*."""
        self._now += seconds


def make_registry(ttl: int = 10, *, clock: FakeClock) -> RelayJobRegistry:
    """Build a registry over the given fake clock."""
    return RelayJobRegistry(job_ttl_seconds=ttl, clock=clock)


class TestRelayJobRegistry:
    """Record storage and TTL-based lazy eviction."""

    def test_put_generates_gateway_id_and_get_roundtrips(self) -> None:
        clock = FakeClock()
        registry = make_registry(clock=clock)
        record = make_record(created_at=clock())
        gateway_job_id = registry.put(record)
        assert isinstance(gateway_job_id, str)
        assert len(gateway_job_id) == 36
        assert registry.get(gateway_job_id) == record

    def test_get_unknown_id_returns_none(self) -> None:
        clock = FakeClock()
        registry = make_registry(clock=clock)
        assert registry.get("no-such-job") is None

    def test_put_issues_distinct_ids(self) -> None:
        clock = FakeClock()
        registry = make_registry(clock=clock)
        first = registry.put(make_record())
        second = registry.put(make_record())
        assert first != second
        assert registry.get(first) is not None
        assert registry.get(second) is not None

    def test_record_within_ttl_is_returned(self) -> None:
        clock = FakeClock()
        registry = make_registry(ttl=10, clock=clock)
        gateway_job_id = registry.put(make_record(created_at=clock()))
        clock.advance(10)
        assert registry.get(gateway_job_id) == make_record(created_at=0.0)

    def test_expired_record_evicted_and_removed_from_storage(self) -> None:
        clock = FakeClock()
        registry = make_registry(ttl=10, clock=clock)
        gateway_job_id = registry.put(make_record(created_at=clock()))
        clock.advance(10.01)
        assert registry.get(gateway_job_id) is None
        assert gateway_job_id not in registry._records
        assert registry._records == {}

    def test_many_expired_lookups_do_not_grow_memory(self) -> None:
        clock = FakeClock()
        registry = make_registry(ttl=10, clock=clock)
        for _ in range(5):
            registry.put(make_record(created_at=clock()))
        clock.advance(60)
        for gateway_job_id in list(registry._records):
            assert registry.get(gateway_job_id) is None
        assert registry._records == {}

    def test_live_records_survive_expired_lookups(self) -> None:
        clock = FakeClock()
        registry = make_registry(ttl=10, clock=clock)
        old_job = registry.put(make_record(created_at=0.0))
        clock.advance(5)
        fresh_job = registry.put(make_record(created_at=clock()))
        clock.advance(6)
        assert registry.get(old_job) is None
        assert registry.get(fresh_job) is not None


class TestRelayGatewayConfigJobTtl:
    """``job_ttl_seconds`` default and validation."""

    def test_defaults_to_one_hour(self) -> None:
        assert RelayGatewayConfig().job_ttl_seconds == 3600

    def test_zero_ttl_rejected(self) -> None:
        with pytest.raises(ValueError, match="job_ttl_seconds"):
            RelayGatewayConfig(job_ttl_seconds=0)

    def test_negative_ttl_rejected(self) -> None:
        with pytest.raises(ValueError, match="job_ttl_seconds"):
            RelayGatewayConfig(job_ttl_seconds=-1)

    def test_positive_ttl_accepted(self) -> None:
        assert RelayGatewayConfig(job_ttl_seconds=120).job_ttl_seconds == 120
