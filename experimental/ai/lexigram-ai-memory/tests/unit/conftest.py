"""Shared test fixtures for lexigram-ai-memory unit tests."""

from __future__ import annotations

import pytest

from lexigram.ai.memory.backends.in_memory import InMemoryMemoryBackend
from lexigram.ai.memory.config import (
    ConsolidationConfig,  # noqa: F401 — re-exported for test convenience
    EpisodicMemoryConfig,  # noqa: F401
    MemoryConfig,
    SemanticMemoryConfig,  # noqa: F401
    WorkingMemoryConfig,  # noqa: F401
)


@pytest.fixture
def backend() -> InMemoryMemoryBackend:
    """Fresh InMemoryMemoryBackend."""
    return InMemoryMemoryBackend()


@pytest.fixture
def default_config() -> MemoryConfig:
    """Default MemoryConfig."""
    return MemoryConfig()
