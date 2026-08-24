import os
from pathlib import Path
import sys

import pytest

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

# Direct sibling-helper imports (e.g. ``admin_bulk_test_support``) resolve
# through this fronted path because pytest's importlib mode does not put
# test directories on sys.path and ``tests/unit`` has no ``__init__.py``.
_UNIT_TESTS_DIR = Path(__file__).resolve().parent / "unit"
if str(_UNIT_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_UNIT_TESTS_DIR))

# ``tests.<subdir>`` namespace imports (scenario/support modules) need the
# admin app root itself on sys.path for package-local pytest runs; the
# repo-root conftest provides it only for monorepo-wide runs.
_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

# Import from the consolidated testing package
from lexigram.testing import TestEnvironment

# Load core testing fixtures
try:
    import importlib

    importlib.import_module("lexigram.testing.fixtures.core")
except ImportError:
    pass


@pytest.fixture
def app():
    """Returns a fresh Application instance for every test."""
    from lexigram.app import Application

    return Application()


@ pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
async def test_bed(app):
    """Returns a TestBed with in-memory drivers pre-configured."""
    bed = TestEnvironment(app)
    async with bed.context():
        yield bed
