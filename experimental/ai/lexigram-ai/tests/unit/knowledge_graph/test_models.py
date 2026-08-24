"""Tests for Entity, Relationship, and GraphPath data models."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.knowledge_graph import (
    Entity,
    EntityType,
    GraphPath,
    Relationship,
    RelationshipType,
)


class TestEntity:
    """Test Entity class."""

    def test_entity_creation(self):
        """Test basic entity creation."""
        entity = Entity(name="Alice", type=EntityType.PERSON)

        assert entity.name == "Alice"
        assert entity.type == EntityType.PERSON
        assert entity.properties == {}
        assert entity.metadata == {}

    def test_entity_with_properties(self):
        """Test entity with properties."""
        entity = Entity(
            name="OpenAI",
            type=EntityType.ORGANIZATION,
            properties={"founded": 2015, "location": "San Francisco"},
            metadata={"source": "text"},
        )

        assert entity.properties["founded"] == 2015
        assert entity.metadata["source"] == "text"

    def test_entity_equality(self):
        """Test entity equality."""
        e1 = Entity("alice", EntityType.PERSON)
        e2 = Entity("Alice", EntityType.PERSON)
        e3 = Entity("Alice", EntityType.ORGANIZATION)

        assert e1 == e2
        assert e1 != e3

    def test_entity_hashable(self):
        """Test entity can be used in sets/dicts."""
        e1 = Entity("Alice", EntityType.PERSON)
        e2 = Entity("Bob", EntityType.PERSON)

        entity_set = {e1, e2}
        assert len(entity_set) == 2
        assert e1 in entity_set


class TestRelationship:
    """Test Relationship class."""

    def test_relationship_creation(self):
        """Test basic relationship creation."""
        rel = Relationship(
            source="Alice",
            target="OpenAI",
            type=RelationshipType.WORKS_AT,
        )

        assert rel.source == "Alice"
        assert rel.target == "OpenAI"
        assert rel.type == RelationshipType.WORKS_AT
        assert rel.confidence == 1.0

    def test_relationship_with_confidence(self):
        """Test relationship with confidence."""
        rel = Relationship(
            source="Alice",
            target="OpenAI",
            type=RelationshipType.WORKS_AT,
            confidence=0.85,
        )

        assert rel.confidence == 0.85

    def test_relationship_equality(self):
        """Test relationship equality."""
        r1 = Relationship("alice", "openai", RelationshipType.WORKS_AT)
        r2 = Relationship("Alice", "OpenAI", RelationshipType.WORKS_AT)
        r3 = Relationship("Alice", "OpenAI", RelationshipType.LOCATED_IN)

        assert r1 == r2
        assert r1 != r3


class TestGraphPath:
    """Test GraphPath."""

    def test_path_creation(self):
        """Test path creation."""
        rels = [
            Relationship("A", "B", RelationshipType.WORKS_AT),
            Relationship("B", "C", RelationshipType.LOCATED_IN),
        ]

        path = GraphPath(
            entities=["A", "B", "C"], relationships=rels, length=2, score=0.9,
        )

        assert len(path.entities) == 3
        assert len(path.relationships) == 2
        assert path.length == 2
        assert path.score == 0.9

    def test_path_repr(self):
        """Test path string representation."""
        rels = [
            Relationship("Alice", "OpenAI", RelationshipType.WORKS_AT),
            Relationship("OpenAI", "SF", RelationshipType.LOCATED_IN),
        ]

        path = GraphPath(
            entities=["Alice", "OpenAI", "SF"], relationships=rels, length=2,
        )

        repr_str = repr(path)
        assert "Alice" in repr_str
        assert "WORKS_AT" in repr_str
        assert "OpenAI" in repr_str
        assert "LOCATED_IN" in repr_str
        assert "SF" in repr_str
