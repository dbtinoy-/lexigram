"""Pytest configuration for cache Result pattern tests."""

import pytest

from lexigram.primitives import clock as ambient_clock
from lexigram.testing.clock import FixedClock

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


# Minimal asyncio marker
if pytest_asyncio:
    pytestmark = pytest.mark.asyncio
