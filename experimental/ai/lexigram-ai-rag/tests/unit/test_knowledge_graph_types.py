"""Tests for knowledge graph types."""

import pytest

from lexigram.ai.rag.knowledge_graph.types import (
    Entity,
    EntityType,
    GraphPath,
    Relationship,
    RelationshipType,
)


class TestEntityType:
    """Tests for EntityType enum."""

    def test_entity_type_values(self) -> None:
        """Test EntityType enum values."""
        assert EntityType.PERSON.value == "PERSON"
        assert EntityType.ORGANIZATION.value == "ORGANIZATION"
        assert EntityType.LOCATION.value == "LOCATION"
        assert EntityType.EVENT.value == "EVENT"
        assert EntityType.PRODUCT.value == "PRODUCT"

    def test_entity_type_members(self) -> None:
        """Test EntityType has expected members."""
        members = list(EntityType)
        assert len(members) >= 6


class TestRelationshipType:
    """Tests for RelationshipType enum."""

    def test_relationship_type_values(self) -> None:
        """Test RelationshipType enum values."""
        assert RelationshipType.WORKS_AT.value == "WORKS_AT"
        assert RelationshipType.LOCATED_IN.value == "LOCATED_IN"
        assert RelationshipType.PART_OF.value == "PART_OF"
        assert RelationshipType.RELATED_TO.value == "RELATED_TO"

    def test_relationship_type_members(self) -> None:
        """Test RelationshipType has expected members."""
        members = list(RelationshipType)
        assert len(members) >= 8


class TestEntity:
    """Tests for Entity dataclass."""

    def test_entity_defaults(self) -> None:
        """Test Entity default values."""
        entity = Entity(name="John")
        assert entity.name == "John"
        assert entity.type == EntityType.OTHER
        assert entity.properties == {}
        assert entity.metadata == {}

    def test_entity_with_type(self) -> None:
        """Test Entity with type."""
        entity = Entity(name="John", type=EntityType.PERSON)
        assert entity.type == EntityType.PERSON

    def test_entity_hash(self) -> None:
        """Test Entity hash."""
        entity1 = Entity(name="John", type=EntityType.PERSON)
        entity2 = Entity(name="John", type=EntityType.PERSON)
        assert hash(entity1) == hash(entity2)

    def test_entity_equality(self) -> None:
        """Test Entity equality."""
        entity1 = Entity(name="John", type=EntityType.PERSON)
        entity2 = Entity(name="John", type=EntityType.PERSON)
        assert entity1 == entity2


class TestRelationship:
    """Tests for Relationship dataclass."""

    def test_relationship_defaults(self) -> None:
        """Test Relationship default values."""
        rel = Relationship(source="A", target="B")
        assert rel.source == "A"
        assert rel.target == "B"
        assert rel.type == RelationshipType.OTHER
        assert rel.confidence == 1.0

    def test_relationship_with_type(self) -> None:
        """Test Relationship with type."""
        rel = Relationship(
            source="John",
            target="Acme",
            type=RelationshipType.WORKS_AT,
        )
        assert rel.type == RelationshipType.WORKS_AT


class TestGraphPath:
    """Tests for GraphPath dataclass."""

    def test_graph_path_defaults(self) -> None:
        """Test GraphPath default values."""
        path = GraphPath(entities=[], relationships=[], length=0)
        assert path.entities == []
        assert path.score == 1.0

    def test_graph_path_repr(self) -> None:
        """Test GraphPath string representation."""
        rel = Relationship(source="A", target="B")
        path = GraphPath(
            entities=["A", "B"],
            relationships=[rel],
            length=1,
        )
        assert "A" in repr(path)
