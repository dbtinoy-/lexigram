"""Shared fixtures for lexigram-vector tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Add the src directory to sys.path BEFORE any imports so pytest can find modules
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import pytest

from lexigram.contracts.data.vector.enums import DistanceMetric
from lexigram.contracts.data.vector.types import (
    CollectionConfig,
    VectorRecord,
)
from lexigram.vector.backends.memory import MemoryVectorStore as InMemoryVectorStore

pytest_plugins = ["lexigram.testing.integration.fixtures"]


@pytest.fixture
async def memory_store() -> InMemoryVectorStore:
    """Create and connect an in-memory vector store."""
    store = InMemoryVectorStore()
    await store.connect()
    yield store
    await store.disconnect()


@pytest.fixture
async def collection(memory_store: InMemoryVectorStore):
    """Create a test collection with 3 dimensions."""
    config = CollectionConfig(
        name="test",
        dimension=3,
        distance_metric=DistanceMetric.COSINE,
    )
    await memory_store.create_collection(config)
    return await memory_store.get_collection("test")


@pytest.fixture
def sample_records() -> list[VectorRecord]:
    """Generate sample vector records."""
    return [
        VectorRecord(
            id="doc-1",
            vector=[1.0, 0.0, 0.0],
            metadata={"category": "science", "year": 2023},
            content="Quantum computing advances",
        ),
        VectorRecord(
            id="doc-2",
            vector=[0.0, 1.0, 0.0],
            metadata={"category": "science", "year": 2024},
            content="AI breakthroughs",
        ),
        VectorRecord(
            id="doc-3",
            vector=[0.0, 0.0, 1.0],
            metadata={"category": "arts", "year": 2023},
            content="Modern art exhibition",
        ),
    ]
