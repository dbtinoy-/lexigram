"""Async fixture decorator selection for the cache testing fixtures.

Centralizes the optional ``pytest_asyncio`` detection so every fixture
module shares one decision about which decorator drives async fixtures.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar, cast

import pytest

P = ParamSpec("P")
R = TypeVar("R")

pytest_asyncio: Any | None
try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None


async_fixture: Callable[..., Any] = (
    pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
)
async_fixture_factory: Callable[..., Callable[[R], R]] = cast(
    "Callable[..., Callable[[R], R]]",
    pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture,
)
