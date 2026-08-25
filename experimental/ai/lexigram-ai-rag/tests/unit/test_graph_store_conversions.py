"""Conversion-helper tests for the ``GraphStoreAdapter`` mappers.

Validates round-trip mapping of ``Entity``/``Relationship``/``GraphPath``
RAG types to and from the infrastructure ``GraphNode``/``GraphEdge``/
``GraphPath`` contracts types.
"""

from __future__ import annotations

import pytest

from lexigram.ai.rag.knowledge_graph.adapter import (
    _edge_to_relationship,
    _entity_to_node_spec,
    _infra_path_to_rag_path,
    _node_to_entity,
    _relationship_to_edge_spec,
)
from lexigram.ai.rag.knowledge_graph.types import (
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
)
from lexigram.contracts.data.graph.types import (
    GraphEdge,
    GraphNode,
    GraphPath as InfraGraphPath,
)


class TestEntityNodeConversions:
    """Round-trip mapping Entity ↔ GraphNode."""

    def test_entity_to_node_spec_label(self, alice_entity: Entity) -> None:
        spec = _entity_to_node_spec(alice_entity)
        assert spec.labels == ("PERSON",)

    def test_entity_to_node_spec_id_is_name_lower(
        self,
        alice_entity: Entity,
    ) -> None:
        spec = _entity_to_node_spec(alice_entity)
        assert spec.id == "alice"

    def test_entity_to_node_spec_properties_include_name(
        self,
        alice_entity: Entity,
    ) -> None:
        spec = _entity_to_node_spec(alice_entity)
        assert spec.properties["name"] == "Alice"
        assert spec.properties["type"] == "PERSON"
        assert spec.properties["age"] == 30

    def test_entity_to_node_spec_metadata_stored(
        self,
        alice_entity: Entity,
    ) -> None:
        spec = _entity_to_node_spec(alice_entity)
        assert spec.properties["__kg_metadata"] == {"source": "doc1"}

    def test_node_to_entity_name(self, alice_node: GraphNode) -> None:
        entity = _node_to_entity(alice_node)
        assert entity.name == "Alice"

    def test_node_to_entity_type(self, alice_node: GraphNode) -> None:
        entity = _node_to_entity(alice_node)
        assert entity.type == EntityType.PERSON

    def test_node_to_entity_extra_properties(
        self,
        alice_node: GraphNode,
    ) -> None:
        entity = _node_to_entity(alice_node)
        assert entity.properties == {"age": 30}

    def test_node_to_entity_metadata_restored(
        self,
        alice_node: GraphNode,
    ) -> None:
        entity = _node_to_entity(alice_node)
        assert entity.metadata == {"source": "doc1"}

    def test_round_trip_entity_preserves_values(
        self,
        alice_entity: Entity,
    ) -> None:
        spec = _entity_to_node_spec(alice_entity)
        # Reconstruct a GraphNode from the spec
        node = GraphNode(
            id=spec.id or "",
            labels=spec.labels,
            properties=spec.properties,
        )
        restored = _node_to_entity(node)
        assert restored.name == alice_entity.name
        assert restored.type == alice_entity.type
        assert restored.properties == alice_entity.properties
        assert restored.metadata == alice_entity.metadata


class TestRelationshipEdgeConversions:
    """Round-trip mapping Relationship ↔ GraphEdge."""

    def test_relationship_to_edge_spec_type(
        self,
        knows_rel: Relationship,
    ) -> None:
        spec = _relationship_to_edge_spec(knows_rel)
        assert spec.type == "RELATED_TO"

    def test_relationship_to_edge_spec_ids_are_lowercased(
        self,
        knows_rel: Relationship,
    ) -> None:
        spec = _relationship_to_edge_spec(knows_rel)
        assert spec.source_id == "alice"
        assert spec.target_id == "bob"

    def test_relationship_to_edge_spec_confidence(
        self,
        knows_rel: Relationship,
    ) -> None:
        spec = _relationship_to_edge_spec(knows_rel)
        assert spec.properties["confidence"] == 0.9

    def test_relationship_to_edge_spec_source_target_names(
        self,
        knows_rel: Relationship,
    ) -> None:
        spec = _relationship_to_edge_spec(knows_rel)
        assert spec.properties["_source_name"] == "Alice"
        assert spec.properties["_target_name"] == "Bob"

    def test_edge_to_relationship_names_restored(
        self,
        knows_edge: GraphEdge,
    ) -> None:
        rel = _edge_to_relationship(knows_edge)
        assert rel.source == "Alice"
        assert rel.target == "Bob"

    def test_edge_to_relationship_type(self, knows_edge: GraphEdge) -> None:
        rel = _edge_to_relationship(knows_edge)
        assert rel.type == RelationshipType.RELATED_TO

    def test_edge_to_relationship_confidence(
        self,
        knows_edge: GraphEdge,
    ) -> None:
        rel = _edge_to_relationship(knows_edge)
        assert rel.confidence == 0.9

    def test_edge_to_relationship_extra_properties(
        self,
        knows_edge: GraphEdge,
    ) -> None:
        rel = _edge_to_relationship(knows_edge)
        assert rel.properties == {"since": 2020}

    def test_edge_to_relationship_metadata_restored(
        self,
        knows_edge: GraphEdge,
    ) -> None:
        rel = _edge_to_relationship(knows_edge)
        assert rel.metadata == {"extractor": "llm"}


class TestInfraPathConversion:
    """Conversion from infrastructure GraphPath to RAG GraphPath."""

    def test_infra_path_to_rag_path_entity_names(
        self,
        alice_node: GraphNode,
        knows_edge: GraphEdge,
    ) -> None:
        bob_node = GraphNode(
            id="bob",
            labels=("PERSON",),
            properties={"name": "Bob", "type": "PERSON"},
        )
        path = InfraGraphPath(
            nodes=(alice_node, bob_node),
            edges=(knows_edge,),
        )
        rag = _infra_path_to_rag_path(path)
        assert rag.entities == ["Alice", "Bob"]

    def test_infra_path_to_rag_path_length(
        self,
        alice_node: GraphNode,
        knows_edge: GraphEdge,
    ) -> None:
        bob_node = GraphNode(
            id="bob",
            labels=("PERSON",),
            properties={"name": "Bob", "type": "PERSON"},
        )
        path = InfraGraphPath(
            nodes=(alice_node, bob_node),
            edges=(knows_edge,),
        )
        rag = _infra_path_to_rag_path(path)
        assert rag.length == 1

    def test_infra_path_to_rag_path_score_from_confidence(
        self,
        alice_node: GraphNode,
        knows_edge: GraphEdge,
    ) -> None:
        bob_node = GraphNode(
            id="bob",
            labels=("PERSON",),
            properties={"name": "Bob", "type": "PERSON"},
        )
        path = InfraGraphPath(
            nodes=(alice_node, bob_node),
            edges=(knows_edge,),
        )
        rag = _infra_path_to_rag_path(path)
        assert rag.score == pytest.approx(0.9)
