"""Tests for knowledge graph functionality — shared fixtures and mocks."""

import pytest

pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

from lexigram.ai.rag.knowledge_graph import (
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
)

try:
    from lexigram.ai.llm.clients.mock import MockLLMClient
except ImportError as e:
    pytest.skip(f"mock llm client unavailable: {e}", allow_module_level=True)

ENTITY_EXTRACTION_RESPONSE = """[
    {"name": "Alice", "type": "PERSON"},
    {"name": "OpenAI", "type": "ORGANIZATION"},
    {"name": "San Francisco", "type": "LOCATION"}
]"""

RELATIONSHIP_EXTRACTION_RESPONSE = """[
    {"source": "Alice", "target": "OpenAI", "type": "WORKS_AT", "confidence": 0.95},
    {"source": "OpenAI", "target": "San Francisco", "type": "LOCATED_IN", "confidence": 0.9}
]"""


@pytest.fixture
def mock_llm_entity():
    """Mock LLM client for entity extraction."""
    return MockLLMClient(responses=[ENTITY_EXTRACTION_RESPONSE])


@pytest.fixture
def mock_llm_relationship():
    """Mock LLM client for relationship extraction."""
    return MockLLMClient(responses=[RELATIONSHIP_EXTRACTION_RESPONSE])


@pytest.fixture
def sample_entities():
    """Sample entities for testing."""
    return [
        Entity("Alice", EntityType.PERSON),
        Entity("Bob", EntityType.PERSON),
        Entity("OpenAI", EntityType.ORGANIZATION),
        Entity("San Francisco", EntityType.LOCATION),
    ]


@pytest.fixture
def sample_relationships():
    """Sample relationships for testing."""
    return [
        Relationship("Alice", "OpenAI", RelationshipType.WORKS_AT, confidence=0.95),
        Relationship("Bob", "OpenAI", RelationshipType.WORKS_AT, confidence=0.9),
        Relationship(
            "OpenAI",
            "San Francisco",
            RelationshipType.LOCATED_IN,
            confidence=0.85,
        ),
    ]


@pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
async def populated_graph(sample_entities, sample_relationships):
    """Knowledge graph populated with test data."""
    from lexigram.ai.rag.knowledge_graph import KnowledgeGraph

    kg = KnowledgeGraph()
    await kg.add_entities(sample_entities)
    await kg.add_relationships(sample_relationships)
    return kg
