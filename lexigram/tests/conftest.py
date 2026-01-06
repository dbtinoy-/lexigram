# tests/conftest.py
from typing import Any

import pytest

pytest_asyncio: Any = None
try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

from lexigram.app import Application

try:
    from lexigram.testing import TestEnvironment
    _testing_available = True
except Exception:
    _testing_available = False
    TestEnvironment = None  # type: ignore[assignment,misc]


@pytest.fixture
def app():
    """Returns a fresh Application instance for every test."""
    return Application()


if _testing_available:
    _fixture = pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture

    @_fixture
    async def test_bed(app):
        """Returns a TestBed with in-memory drivers pre-configured."""
        async with TestEnvironment(app) as bed:
            yield bed
