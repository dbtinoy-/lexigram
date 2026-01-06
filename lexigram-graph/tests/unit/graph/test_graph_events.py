from __future__ import annotations

import uuid
from datetime import datetime, timezone

from lexigram.graph.events import (
    GraphConnectedEvent,
    GraphDisconnectedEvent,
    GraphEdgeCreatedEvent,
    GraphNodeCreatedEvent,
    GraphQueryExecutedEvent,
)


class TestGraphConnectedEvent:
    def test_graph_connected_event_creation(self) -> None:
        event = GraphConnectedEvent(backend="neo4j")
        assert event.backend == "neo4j"
        assert event.occurred_at is not None

    def test_graph_connected_event_has_event_id(self) -> None:
        event = GraphConnectedEvent(backend="neo4j")
        assert event.event_id is not None
        assert isinstance(event.event_id, uuid.UUID)

    def test_graph_connected_event_schema_version(self) -> None:
        event = GraphConnectedEvent(backend="neo4j")
        assert event.schema_version == 1


class TestGraphDisconnectedEvent:
    def test_graph_disconnected_event_creation(self) -> None:
        event = GraphDisconnectedEvent(backend="neo4j")
        assert event.backend == "neo4j"
        assert event.occurred_at is not None

    def test_graph_disconnected_event_has_event_id(self) -> None:
        event = GraphDisconnectedEvent(backend="memory")
        assert event.event_id is not None


class TestGraphNodeCreatedEvent:
    def test_graph_node_created_event_creation(self) -> None:
        node_id = str(uuid.uuid4())
        labels = ("Person", "User")
        event = GraphNodeCreatedEvent(node_id=node_id, labels=labels)
        assert event.node_id == node_id
        assert event.labels == labels

    def test_graph_node_created_event_with_single_label(self) -> None:
        event = GraphNodeCreatedEvent(node_id="123", labels=("User",))
        assert len(event.labels) == 1
        assert event.labels[0] == "User"

    def test_graph_node_created_event_has_event_id(self) -> None:
        event = GraphNodeCreatedEvent(node_id="123", labels=("Test",))
        assert event.event_id is not None


class TestGraphEdgeCreatedEvent:
    def test_graph_edge_created_event_creation(self) -> None:
        event = GraphEdgeCreatedEvent(
            source_id="source-123",
            target_id="target-456",
            relationship_type="KNOWS",
        )
        assert event.source_id == "source-123"
        assert event.target_id == "target-456"
        assert event.relationship_type == "KNOWS"

    def test_graph_edge_created_event_has_event_id(self) -> None:
        event = GraphEdgeCreatedEvent(
            source_id="1",
            target_id="2",
            relationship_type="FOLLOWS",
        )
        assert event.event_id is not None


class TestGraphQueryExecutedEvent:
    def test_graph_query_executed_event_creation(self) -> None:
        event = GraphQueryExecutedEvent(
            query_type="cypher",
            result_count=10,
        )
        assert event.query_type == "cypher"
        assert event.result_count == 10

    def test_graph_query_executed_event_with_zero_count(self) -> None:
        event = GraphQueryExecutedEvent(query_type="cypher", result_count=0)
        assert event.result_count == 0

    def test_graph_query_executed_event_has_event_id(self) -> None:
        event = GraphQueryExecutedEvent(query_type="cypher", result_count=5)
        assert event.event_id is not None


class TestGraphEventsOccurredAt:
    def test_occurred_at_is_set(self) -> None:
        before = datetime.now(timezone.utc)
        event = GraphConnectedEvent(backend="neo4j")
        after = datetime.now(timezone.utc)
        assert before <= event.occurred_at <= after

    def test_occurred_at_format(self) -> None:
        event = GraphConnectedEvent(backend="neo4j")
        assert event.occurred_at.tzinfo is not None