# tests/conftest.py
import os
import sys
from pathlib import Path

import pytest

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None


# Resolve dependencies via uv workspace
BASE_DIR = Path(__file__).parent

from lexigram.testing import TestEnvironment
from lexigram.testing.fixtures.core import *  # noqa: F403
from lexigram.testing.fixtures.tasks import (
    sample_task_data,
    task_test_bed,
    task_test_client,
)

__all__ = [
    "tasks_test_bed",
    "test_bed",
    "sample_task_data",
    "task_test_bed",
    "task_test_client",
]


@ pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
async def test_bed():
    """Async TestBed fixture for testing."""
    bed = TestEnvironment()
    async with bed.context():
        yield bed


@ pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
async def tasks_test_bed():
    """Async TestBed fixture specifically for tasks testing."""
    bed = TestEnvironment()
    async with bed.context():
        yield bed
