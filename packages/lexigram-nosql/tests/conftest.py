"""Shared test configuration and fixtures."""
from pathlib import Path
import sys
from unittest.mock import MagicMock

import pytest

# Set up pymongo stubs early so that any import of lexigram.nosql.backends.mongodb
# works without the real pymongo installed.  We use real Exception subclasses so
# that except clauses in the source code can catch them.
_PyMongoError = type("PyMongoError", (Exception,), {})
_DuplicateKeyError = type("DuplicateKeyError", (_PyMongoError,), {})

_pymongo_errors = MagicMock()
_pymongo_errors.PyMongoError = _PyMongoError
_pymongo_errors.DuplicateKeyError = _DuplicateKeyError

_pymongo_mod = MagicMock()
_pymongo_mod.errors = _pymongo_errors

sys.modules.setdefault("pymongo", _pymongo_mod)
sys.modules.setdefault("pymongo.errors", _pymongo_errors)
sys.modules.setdefault("motor", MagicMock())
sys.modules.setdefault("motor.motor_asyncio", MagicMock())

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


@pytest.fixture
def app():
    """Returns a fresh Application instance for every test."""
    from lexigram.app import Application

    return Application()


@pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
async def test_bed(app):
    """Returns a TestBed with in-memory drivers pre-configured."""
    async with TestEnvironment(app) as bed:
        yield bed
