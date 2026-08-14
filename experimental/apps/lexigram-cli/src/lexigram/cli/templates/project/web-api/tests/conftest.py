"""Pytest configuration for {{ project_name }}."""
from __future__ import annotations

import pytest


@pytest.fixture
def anyio_backend():
    """Use asyncio backend for all async tests."""
    return "asyncio"
