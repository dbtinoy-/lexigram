"""Fake implementations for testing."""

from __future__ import annotations

from lexigram.testing.fakes.audit import FakeAuditLogger
from lexigram.testing.fakes.buses import FakeCommandBus, FakeQueryBus
from lexigram.testing.fakes.cache import FakeCache, FakeStateStore
from lexigram.testing.fakes.clock import Clock, FakeClock, SystemClock
from lexigram.testing.fakes.config import FakeConfig
from lexigram.testing.fakes.events import FakeEventBus
from lexigram.testing.fakes.governance import FakeResourceUnitTracker
from lexigram.testing.fakes.lifecycle import FakeUnitOfWork
from lexigram.testing.fakes.logging import FakeLogger, LogEntry
from lexigram.testing.fakes.monitoring import FakeMetricsCollector
from lexigram.testing.fakes.redis import FakeRedisClient
from lexigram.testing.fakes.secrets import FakeRotatableSecretStore
from lexigram.testing.fakes.tracing import FakeSpan, FakeTracer

__all__ = [
    "Clock",
    "FakeAuditLogger",
    "FakeCache",
    "FakeClock",
    "FakeCommandBus",
    "FakeConfig",
    "FakeEventBus",
    "FakeLogger",
    "FakeMetricsCollector",
    "FakeQueryBus",
    "FakeRedisClient",
    "FakeResourceUnitTracker",
    "FakeRotatableSecretStore",
    "FakeSpan",
    "FakeStateStore",
    "FakeTracer",
    "FakeUnitOfWork",
    "LogEntry",
    "SystemClock",
]
