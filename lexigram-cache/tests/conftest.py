from pathlib import Path
import sys

import pytest

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

# Import from the consolidated testing package
from lexigram.testing import TestEnvironment

# Load core testing fixtures
try:
    import importlib

    importlib.import_module("lexigram.testing.fixtures.core")
except ImportError:
    pass

# Load integration fixtures for infrastructure services
pytest_plugins = ["lexigram.testing.integration.fixtures"]


@pytest.fixture
def app():
    """Returns a fresh Application instance for every test."""
    from lexigram.app import Application

    return Application()


@ pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
async def test_bed(app):
    """Returns a TestEnvironment with in-memory drivers pre-configured."""
    bed = TestEnvironment(app)
    async with bed.context():
        yield bed
