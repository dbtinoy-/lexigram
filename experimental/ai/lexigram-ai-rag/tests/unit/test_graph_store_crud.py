"""CRUD-method tests for ``GraphStoreAdapter``.

Validates that add/get/list operations delegate to the underlying
``GraphProtocol`` with correctly mapped arguments.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.ai.rag.knowledge_graph.adapter import GraphStoreAdapter
from lexigram.ai.rag.knowledge_graph.types import (
    Entity,
    EntityType,
    Relationship,
)
from lexigram.contracts.data.graph.types import GraphNode


class TestAddEntity:
    """Adapter.add_entity delegates to GraphProtocol.bulk_create_nodes."""

    @pytest.mark.asyncio
    async def test_add_entity_creates_new_node(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_entity: Entity,
    ) -> None:
        mock_graph.get_node.return_value = None
        await adapter.add_entity(alice_entity)

        mock_graph.bulk_create_nodes.assert_awaited_once()
        spec = mock_graph.bulk_create_nodes.call_args[0][0][0]
        assert spec.id == "alice"
        assert "PERSON" in spec.labels

    @pytest.mark.asyncio
    async def test_add_entity_upserts_existing_node(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_entity: Entity,
        alice_node: GraphNode,
    ) -> None:
        mock_graph.get_node.return_value = alice_node
        await adapter.add_entity(alice_entity)

        mock_graph.update_node.assert_awaited_once()
        node_id, kwargs = (
            mock_graph.update_node.call_args[0][0],
            mock_graph.update_node.call_args[1],
        )
        assert node_id == "alice"
        assert kwargs.get("merge") is True


class TestAddRelationship:
    """Adapter.add_relationship delegates to GraphProtocol.create_edge."""

    @pytest.mark.asyncio
    async def test_add_relationship_creates_edge(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        knows_rel: Relationship,
    ) -> None:
        await adapter.add_relationship(knows_rel)

        mock_graph.create_edge.assert_awaited_once_with(
            source_id="alice",
            target_id="bob",
            edge_type="RELATED_TO",
            properties=mock_graph.create_edge.call_args[1]["properties"],
        )

    @pytest.mark.asyncio
    async def test_add_relationship_logs_warning_on_missing_node(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        knows_rel: Relationship,
    ) -> None:
        """If source/target node is missing, skip silently with a warning."""
        mock_graph.create_edge.side_effect = RuntimeError("node not found")
        # Should not raise — missing relationships are warned and skipped.
        await adapter.add_relationship(knows_rel)


class TestGetEntity:
    """Adapter.get_entity delegates to GraphProtocol.get_node."""

    @pytest.mark.asyncio
    async def test_get_entity_returns_entity_when_found(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_node: GraphNode,
    ) -> None:
        mock_graph.get_node.return_value = alice_node
        entity = await adapter.get_entity("Alice")

        mock_graph.get_node.assert_awaited_once_with("alice")
        assert entity is not None
        assert entity.name == "Alice"

    @pytest.mark.asyncio
    async def test_get_entity_returns_none_when_missing(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
    ) -> None:
        mock_graph.get_node.return_value = None
        entity = await adapter.get_entity("Nonexistent")
        assert entity is None


class TestGetAllEntities:
    """Adapter.get_all_entities delegates to GraphProtocol.find_nodes."""

    @pytest.mark.asyncio
    async def test_get_all_entities_converts_nodes(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_node: GraphNode,
    ) -> None:
        mock_graph.find_nodes.return_value = [alice_node]
        entities = await adapter.get_all_entities()

        assert len(entities) == 1
        assert entities[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_get_all_entities_empty_graph(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
    ) -> None:
        mock_graph.find_nodes.return_value = []
        entities = await adapter.get_all_entities()
        assert entities == []


class TestGetEntitiesByType:
    """Adapter.get_entities_by_type filters by label."""

    @pytest.mark.asyncio
    async def test_get_entities_by_type_calls_find_nodes_with_label(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_node: GraphNode,
    ) -> None:
        mock_graph.find_nodes.return_value = [alice_node]
        entities = await adapter.get_entities_by_type(EntityType.PERSON)

        mock_graph.find_nodes.assert_awaited_once_with(
            labels=["PERSON"],
            limit=10_000,
        )
        assert len(entities) == 1


class TestAddEntities:
    """Adapter.add_entities processes a list."""

    @pytest.mark.asyncio
    async def test_add_entities_calls_add_for_each(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_entity: Entity,
        bob_entity: Entity,
    ) -> None:
        mock_graph.get_node.return_value = None
        await adapter.add_entities([alice_entity, bob_entity])
        assert mock_graph.bulk_create_nodes.await_count == 2


class TestAddRelationships:
    """Adapter.add_relationships processes a list."""

    @pytest.mark.asyncio
    async def test_add_relationships_calls_add_for_each(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        knows_rel: Relationship,
    ) -> None:
        await adapter.add_relationships([knows_rel, knows_rel])
        assert mock_graph.create_edge.await_count == 2
