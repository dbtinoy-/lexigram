"""Tests for knowledge graph functionality."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

from lexigram.ai.rag.knowledge_graph import (
    Entity,
    EntityExtractor,
    EntityType,
    GraphPath,
    GraphRAGIntegration,
    KnowledgeGraph,
    KnowledgeGraphBuilder,
    Relationship,
    RelationshipExtractor,
    RelationshipType,
)
from lexigram.result import Ok
try:
    from lexigram.ai.llm.clients.mock import MockLLMClient
except ImportError as e:
    pytest.skip(f"mock llm client unavailable: {e}", allow_module_level=True)

# Mock responses for entity extraction
ENTITY_EXTRACTION_RESPONSE = """[
    {"name": "Alice", "type": "PERSON"},
    {"name": "OpenAI", "type": "ORGANIZATION"},
    {"name": "San Francisco", "type": "LOCATION"}
]"""

# Mock responses for relationship extraction
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
    kg = KnowledgeGraph()
    await kg.add_entities(sample_entities)
    await kg.add_relationships(sample_relationships)
    return kg


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

        assert e1 == e2  # Case insensitive
        assert e1 != e3  # Different types

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

        assert r1 == r2  # Case insensitive
        assert r1 != r3  # Different types


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

        # Should still extract all entities from mock response
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
    async def test_extract_with_entities(
        self,
        mock_llm_relationship,
        sample_entities,
    ):
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

        # Should filter out relationships with confidence < 0.99
        assert (
            all(r.confidence >= 0.99 for r in relationships) or len(relationships) == 0
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
    async def test_add_relationships(self, sample_relationships):
        """Test adding multiple relationships."""
        kg = KnowledgeGraph()

        await kg.add_relationships(sample_relationships)

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

        assert len(neighbors) == 2  # Alice and Bob both work at OpenAI
        names = {n.name for n in neighbors}
        assert "Alice" in names
        assert "Bob" in names

    @pytest.mark.asyncio
    async def test_get_neighbors_both(self, populated_graph):
        """Test getting neighbors in both directions."""
        neighbors = await populated_graph.get_neighbors("OpenAI", direction="both")

        assert len(neighbors) == 3  # Alice, Bob (incoming), San Francisco (outgoing)

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
        # Add disconnected entity
        await populated_graph.add_entity(Entity("Charlie", EntityType.PERSON))

        path = await populated_graph.find_path("Alice", "Charlie")

        assert path is None

    @pytest.mark.asyncio
    async def test_find_path_max_depth(self, populated_graph):
        """Test path with depth limit."""
        path = await populated_graph.find_path("Alice", "San Francisco", max_depth=1)

        # Path requires 2 hops, so won't be found with max_depth=1
        assert path is None

    @pytest.mark.asyncio
    async def test_find_all_paths(self):
        """Test finding all paths."""
        kg = KnowledgeGraph()

        # Create graph with multiple paths
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

        assert len(paths) == 2  # A->B->D and A->C->D
        assert all(p.entities[0] == "A" and p.entities[-1] == "D" for p in paths)

    @pytest.mark.asyncio
    async def test_query_subgraph(self, populated_graph):
        """Test querying subgraph around entity."""
        entities, relationships = await populated_graph.query_subgraph(
            "OpenAI", depth=1,
        )

        # Should include OpenAI, Alice, Bob (incoming), San Francisco (outgoing)
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


class TestKnowledgeGraphBuilder:
    """Test KnowledgeGraphBuilder."""

    @pytest.mark.asyncio
    async def test_build_from_text(self):
        """Test building graph from text."""
        mock_llm = MockLLMClient(
            responses=[ENTITY_EXTRACTION_RESPONSE, RELATIONSHIP_EXTRACTION_RESPONSE],
        )

        builder = KnowledgeGraphBuilder(llm_client=mock_llm)
        text = "Alice works at OpenAI in San Francisco."

        kg = await builder.build_from_text(text)

        assert len(kg) == 3  # 3 entities
        stats = kg.get_stats()
        assert stats["total_relationships"] == 2

    @pytest.mark.asyncio
    async def test_build_from_documents_merged(self):
        """Test building graph from multiple documents (merged)."""
        mock_llm = MockLLMClient(
            responses=[
                ENTITY_EXTRACTION_RESPONSE,
                RELATIONSHIP_EXTRACTION_RESPONSE,
                ENTITY_EXTRACTION_RESPONSE,
                RELATIONSHIP_EXTRACTION_RESPONSE,
            ],
        )

        builder = KnowledgeGraphBuilder(llm_client=mock_llm)
        documents = [
            "Alice works at OpenAI in San Francisco.",
            "Alice works at OpenAI in San Francisco.",  # Duplicate for testing
        ]

        kg = await builder.build_from_documents(documents, merge=True)

        assert isinstance(kg, KnowledgeGraph)
        assert len(kg) >= 3

    @pytest.mark.asyncio
    async def test_build_from_documents_separate(self):
        """Test building separate graphs from documents."""
        mock_llm = MockLLMClient(
            responses=[
                ENTITY_EXTRACTION_RESPONSE,
                RELATIONSHIP_EXTRACTION_RESPONSE,
                ENTITY_EXTRACTION_RESPONSE,
                RELATIONSHIP_EXTRACTION_RESPONSE,
            ],
        )

        builder = KnowledgeGraphBuilder(llm_client=mock_llm)
        documents = [
            "Alice works at OpenAI.",
            "Bob works at Google.",
        ]

        graphs = await builder.build_from_documents(documents, merge=False)

        assert isinstance(graphs, list)
        assert len(graphs) == 2
        assert all(isinstance(g, KnowledgeGraph) for g in graphs)


class TestGraphRAGIntegration:
    """Test GraphRAGIntegration."""

    @pytest.mark.asyncio
    async def test_expand_query_with_graph(self, populated_graph):
        """Test query expansion using graph."""
        mock_llm = MockLLMClient(responses=[ENTITY_EXTRACTION_RESPONSE])

        # Mock vector store
        class MockVectorStore:
            async def search(self, query, top_k=5):
                return Ok([])

        integration = GraphRAGIntegration(
            knowledge_graph=populated_graph,
            vector_store=MockVectorStore(),
            llm_client=mock_llm,
        )

        expanded = await integration.expand_query_with_graph(
            "Alice works at OpenAI",
            max_expansions=3,
        )

        assert len(expanded) >= 1
        assert expanded[0] == "Alice works at OpenAI"  # Original

    @pytest.mark.asyncio
    async def test_retrieve_with_graph(self, populated_graph):
        """Test graph-enhanced retrieval."""
        mock_llm = MockLLMClient(responses=[ENTITY_EXTRACTION_RESPONSE])

        # Mock vector store
        class MockVectorStore:
            async def search(self, query, top_k=5):
                # Return mock results
                class MockResult:
                    def __init__(self, id, text):
                        self.id = id
                        self.text = text

                return Ok(
                    list(map(lambda i: MockResult(i, f"Result {i}"), range(top_k))),
                )

        integration = GraphRAGIntegration(
            knowledge_graph=populated_graph,
            vector_store=MockVectorStore(),
            llm_client=mock_llm,
        )

        results = await integration.retrieve_with_graph(
            "test query", top_k=3, expand=False,
        )

        assert len(results) == 3
