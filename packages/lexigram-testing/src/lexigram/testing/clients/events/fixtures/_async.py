"""Async fixture decorator selection for the events testing fixtures.

Centralizes the optional ``pytest_asyncio`` detection so every fixture
module shares one decision about which decorator drives async fixtures.
"""

from __future__ import annotations

# mypy: disable-error-code = annotation-unchecked
from collections.abc import Callable
from types import ModuleType
from typing import Any

import pytest

from lexigram.logging import get_logger

logger = get_logger(__name__)

# Annotate as ModuleType | None to avoid mypy assignment errors when import fails
pytest_asyncio: ModuleType | None = None
try:
    import pytest_asyncio
except (ImportError, ModuleNotFoundError, AttributeError) as e:
    # Leave as None when unavailable
    import contextlib

    with contextlib.suppress(OSError, ValueError, TypeError):
        logger.debug("pytest_asyncio import unavailable: %s", e)

# Async fixtures must use pytest_asyncio.fixture in strict asyncio mode.
async_fixture: Callable[..., Any] = (
    pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
)
