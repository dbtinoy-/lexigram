"""Async fixture decorator selection for the auth testing fixtures.

Centralizes the optional ``pytest_asyncio`` detection so every fixture
module shares one decision about which decorator drives async fixtures.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from lexigram.logging import get_logger

logger = get_logger(__name__)

pytest_asyncio: Any | None = None
try:
    import pytest_asyncio as _pytest_asyncio

    pytest_asyncio = _pytest_asyncio
except ImportError as e:
    logger.warning("pytest_asyncio not available: %s", e)
    pytest_asyncio = None

# Choose the async fixture decorator depending on pytest-asyncio availability
async_fixture: Callable[..., Any] = (
    pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
)
