"""Tests for EntityExtractor and RelationshipExtractor."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.knowledge_graph import (
    EntityType,
    EntityExtractor,
    RelationshipExtractor,
    RelationshipType,
)
ENTITY_EXTRACTION_RESPONSE = """[
    {"name": "Alice", "type": "PERSON"},
    {"name": "OpenAI", "type": "ORGANIZATION"},
    {"name": "San Francisco", "type": "LOCATION"}
]"""

RELATIONSHIP_EXTRACTION_RESPONSE = """[
    {"source": "Alice", "target": "OpenAI", "type": "WORKS_AT", "confidence": 0.95},
    {"source": "OpenAI", "target": "San Francisco", "type": "LOCATED_IN", "confidence": 0.9}
]"""


class TestEntityExtractor:
    """Test EntityExtractor."""

    @pytest.mark.asyncio
    async def test_extract_entities(self, mock_llm_entity):
        """Test entity extraction from text."""
        extractor = EntityExtractor(llm_client=mock_llm_entity)

        text = "Alice works at OpenAI in San Francisco."
        entities = await extractor.extract(text)

        assert len(entities) == 3
        assert any(e.name == "Alice" and e.type == EntityType.PERSON for e in entities)
        assert any(
            e.name == "OpenAI" and e.type == EntityType.ORGANIZATION for e in entities
        )
        assert any(
            e.name == "San Francisco" and e.type == EntityType.LOCATION
            for e in entities
        )

    @pytest.mark.asyncio
    async def test_extract_with_entity_types(self, mock_llm_entity):
        """Test extraction with specific entity types."""
        extractor = EntityExtractor(
            llm_client=mock_llm_entity,
            entity_types=[EntityType.PERSON],
        )

        text = "Alice works at OpenAI."
        entities = await extractor.extract(text)

        assert len(entities) >= 1


class TestRelationshipExtractor:
    """Test RelationshipExtractor."""

    @pytest.mark.asyncio
    async def test_extract_relationships(self, mock_llm_relationship):
        """Test relationship extraction from text."""
        extractor = RelationshipExtractor(llm_client=mock_llm_relationship)

        text = "Alice works at OpenAI in San Francisco."
        relationships = await extractor.extract(text)

        assert len(relationships) == 2
        assert any(
            r.source == "Alice"
            and r.target == "OpenAI"
            and r.type == RelationshipType.WORKS_AT
            for r in relationships
        )

    @pytest.mark.asyncio
    async def test_extract_with_entities(self, mock_llm_relationship, sample_entities):
        """Test extraction with known entities."""
        extractor = RelationshipExtractor(llm_client=mock_llm_relationship)

        text = "Alice works at OpenAI."
        relationships = await extractor.extract(text, entities=sample_entities[:3])

        assert len(relationships) >= 1

    @pytest.mark.asyncio
    async def test_confidence_filtering(self, mock_llm_relationship):
        """Test confidence threshold filtering."""
        extractor = RelationshipExtractor(
            llm_client=mock_llm_relationship,
            min_confidence=0.99,
        )

        text = "Alice works at OpenAI."
        relationships = await extractor.extract(text)

        assert (
            all(r.confidence >= 0.99 for r in relationships) or len(relationships) == 0
        )
