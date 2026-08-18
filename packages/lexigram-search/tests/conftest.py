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

# Load core testing fixtures
try:
    import importlib

    importlib.import_module("lexigram.testing.fixtures.core")
except ImportError:
    pass

# Load integration fixtures for infrastructure services

from lexigram.testing import TestEnvironment


@ pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
async def test_bed():
    """Async TestBed fixture for testing."""
    bed = TestEnvironment()
    async with bed.context():
        yield bed
