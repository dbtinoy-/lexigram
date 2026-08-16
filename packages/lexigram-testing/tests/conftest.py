"""Test fixtures for lexigram-testing."""
import pytest

from lexigram.testing import TestEnvironment


@pytest.fixture
def test_env():
    """Create a clean test environment."""
    return TestEnvironment()