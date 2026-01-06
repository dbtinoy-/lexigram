"""Shared pytest fixtures for lexigram-example-platform tests."""

from __future__ import annotations

import pytest


@pytest.fixture()
def anyio_backend() -> str:
    """Use asyncio as the anyio backend."""
    return "asyncio"
