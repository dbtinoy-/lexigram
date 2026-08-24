"""Tests for KnowledgeGraph."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.knowledge_graph import (
    Entity,
    EntityType,
    KnowledgeGraph,
    Relationship,
    RelationshipType,
)



class TestKnowledgeGraph:
    """Test KnowledgeGraph."""

    @pytest.mark.asyncio
    async def test_empty_graph(self):
        """Test empty graph creation."""
        kg = KnowledgeGraph()

        assert len(kg) == 0
        assert kg.get_stats()["total_entities"] == 0
        assert kg.get_stats()["total_relationships"] == 0

    @pytest.mark.asyncio
    async def test_add_entity(self):
        """Test adding entity to graph."""
        kg = KnowledgeGraph()
        entity = Entity("Alice", EntityType.PERSON)

        await kg.add_entity(entity)

        assert len(kg) == 1
        retrieved = await kg.get_entity("Alice")
        assert retrieved == entity

    @pytest.mark.asyncio
    async def test_add_entities(self, sample_entities):
        """Test adding multiple entities."""
        kg = KnowledgeGraph()

        await kg.add_entities(sample_entities)

        assert len(kg) == 4

    @pytest.mark.asyncio
    async def test_get_entity_case_insensitive(self):
        """Test entity retrieval is case-insensitive."""
        kg = KnowledgeGraph()
        entity = Entity("Alice", EntityType.PERSON)
        await kg.add_entity(entity)

        retrieved = await kg.get_entity("alice")
        assert retrieved == entity

        retrieved = await kg.get_entity("ALICE")
        assert retrieved == entity

    @pytest.mark.asyncio
    async def test_get_entities_by_type(self, populated_graph):
        """Test getting entities by type."""
        people = await populated_graph.get_entities_by_type(EntityType.PERSON)
        orgs = await populated_graph.get_entities_by_type(EntityType.ORGANIZATION)
        locations = await populated_graph.get_entities_by_type(EntityType.LOCATION)

        assert len(people) == 2
        assert len(orgs) == 1
        assert len(locations) == 1

    @pytest.mark.asyncio
    async def test_add_relationship(self):
        """Test adding relationship."""
        kg = KnowledgeGraph()
        rel = Relationship("Alice", "OpenAI", RelationshipType.WORKS_AT)

        await kg.add_relationship(rel)

        rels = await kg.get_relationships("Alice")
        assert len(rels) == 1
        assert rels[0] == rel

    @pytest.mark.asyncio
    async def test_add_relationships(self, populated_graph):
        """Test adding multiple relationships."""
        kg = KnowledgeGraph()

        rels = [
            Relationship("Alice", "OpenAI", RelationshipType.WORKS_AT),
            Relationship("Bob", "OpenAI", RelationshipType.WORKS_AT),
        ]
        await kg.add_relationships(rels)

        alice_rels = await kg.get_relationships("Alice")
        assert len(alice_rels) == 1

    @pytest.mark.asyncio
    async def test_get_neighbors_outgoing(self, populated_graph):
        """Test getting outgoing neighbors."""
        neighbors = await populated_graph.get_neighbors("Alice", direction="outgoing")

        assert len(neighbors) == 1
        assert neighbors[0].name == "OpenAI"

    @pytest.mark.asyncio
    async def test_get_neighbors_incoming(self, populated_graph):
        """Test getting incoming neighbors."""
        neighbors = await populated_graph.get_neighbors("OpenAI", direction="incoming")

        assert len(neighbors) == 2
        names = {n.name for n in neighbors}
        assert "Alice" in names
        assert "Bob" in names

    @pytest.mark.asyncio
    async def test_get_neighbors_both(self, populated_graph):
        """Test getting neighbors in both directions."""
        neighbors = await populated_graph.get_neighbors("OpenAI", direction="both")

        assert len(neighbors) == 3

    @pytest.mark.asyncio
    async def test_find_path(self, populated_graph):
        """Test finding shortest path."""
        path = await populated_graph.find_path("Alice", "San Francisco")

        assert path is not None
        assert path.length == 2
        assert path.entities == ["Alice", "OpenAI", "San Francisco"]
        assert len(path.relationships) == 2

    @pytest.mark.asyncio
    async def test_find_path_direct(self, populated_graph):
        """Test finding direct path."""
        path = await populated_graph.find_path("Alice", "OpenAI")

        assert path is not None
        assert path.length == 1
        assert path.entities == ["Alice", "OpenAI"]

    @pytest.mark.asyncio
    async def test_find_path_not_found(self, populated_graph):
        """Test path not found."""
        await populated_graph.add_entity(Entity("Charlie", EntityType.PERSON))

        path = await populated_graph.find_path("Alice", "Charlie")

        assert path is None

    @pytest.mark.asyncio
    async def test_find_path_max_depth(self, populated_graph):
        """Test path with depth limit."""
        path = await populated_graph.find_path("Alice", "San Francisco", max_depth=1)

        assert path is None

    @pytest.mark.asyncio
    async def test_find_all_paths(self):
        """Test finding all paths."""
        kg = KnowledgeGraph()

        await kg.add_entities(
            [
                Entity("A", EntityType.PERSON),
                Entity("B", EntityType.PERSON),
                Entity("C", EntityType.PERSON),
                Entity("D", EntityType.PERSON),
            ],
        )

        await kg.add_relationships(
            [
                Relationship("A", "B", RelationshipType.RELATED_TO),
                Relationship("B", "D", RelationshipType.RELATED_TO),
                Relationship("A", "C", RelationshipType.RELATED_TO),
                Relationship("C", "D", RelationshipType.RELATED_TO),
            ],
        )

        paths = await kg.find_all_paths("A", "D", max_depth=3, max_paths=10)

        assert len(paths) == 2
        assert all(p.entities[0] == "A" and p.entities[-1] == "D" for p in paths)

    @pytest.mark.asyncio
    async def test_query_subgraph(self, populated_graph):
        """Test querying subgraph around entity."""
        entities, relationships = await populated_graph.query_subgraph(
            "OpenAI", depth=1,
        )

        assert len(entities) == 4
        assert len(relationships) == 3

    @pytest.mark.asyncio
    async def test_graph_stats(self, populated_graph):
        """Test graph statistics."""
        stats = populated_graph.get_stats()

        assert stats["total_entities"] == 4
        assert stats["total_relationships"] == 3
        assert stats["entity_counts"][str(EntityType.PERSON)] == 2
        assert stats["entity_counts"][str(EntityType.ORGANIZATION)] == 1
        assert "created_at" in stats
        assert "updated_at" in stats

    @pytest.mark.asyncio
    async def test_graph_repr(self, populated_graph):
        """Test graph string representation."""
        repr_str = repr(populated_graph)

        assert "KnowledgeGraph" in repr_str
        assert "entities=4" in repr_str
        assert "relationships=3" in repr_str
