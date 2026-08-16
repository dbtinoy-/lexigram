"""Pytest configuration for cache Result pattern tests."""

import pytest

from lexigram.primitives import clock as ambient_clock
from lexigram.testing.clock import FixedClock
from lexigram.testing.fakes.redis import FakeRedisClient

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None


@pytest.fixture(autouse=True)
def setup_ambient_clock():
    """Set up ambient clock for all tests."""
    fixed = FixedClock()
    with ambient_clock.use(fixed):
        yield


@pytest.fixture
def redis_fake() -> FakeRedisClient:
    """Return an isolated in-process Redis-compatible client for this test."""
    return FakeRedisClient()


# Minimal asyncio marker
if pytest_asyncio:
    pytestmark = pytest.mark.asyncio
