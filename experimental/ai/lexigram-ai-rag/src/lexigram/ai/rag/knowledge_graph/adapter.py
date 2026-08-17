"""Knowledge-graph adapter backed by ``GraphStoreProtocol``.

Wraps a ``GraphProtocol`` instance (resolved from the DI container via
``lexigram-graph``) and exposes the same interface as ``KnowledgeGraph``,
mapping between the RAG-layer ``Entity``/``Relationship``/``GraphPath``
domain types and the infrastructure ``GraphNode``/``GraphEdge``/``GraphPath``
contracts types.

When ``GraphStoreProtocol`` is registered in the container (e.g. by
``GraphModule`` / ``GraphProvider``), ``RAGProvider`` automatically creates
this adapter and registers it as the singleton ``KnowledgeGraph`` — giving
the RAG pipeline a fully persistent graph back-end.  When the infra store
is absent, ``RAGProvider`` falls back to the in-memory ``KnowledgeGraph``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.rag.knowledge_graph.types import (
    Entity,
    EntityType,
    GraphPath,
    Relationship,
    RelationshipType,
)
from lexigram.contracts.data.graph.enums import EdgeDirection
from lexigram.contracts.data.graph.types import (
    EdgeSpec,
    NodeSpec,
    StartSpec,
    TraversalQuery,
    TraversalStep,
)
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.data.graph.protocols import GraphProtocol
    from lexigram.contracts.data.graph.types import (
        GraphEdge,
        GraphNode,
    )
    from lexigram.contracts.data.graph.types import (
        GraphPath as InfraGraphPath,
    )

logger = get_logger(__name__)

# Property keys stored alongside entity data but excluded from the
# round-tripped ``Entity.properties`` dict.
_META_KEY = "__kg_metadata"
_NAME_KEY = "name"
_TYPE_KEY = "type"
_SRC_KEY = "_source_name"
_TGT_KEY = "_target_name"
_CONF_KEY = "confidence"

_RESERVED_NODE_KEYS = frozenset({_META_KEY, _NAME_KEY, _TYPE_KEY})
_RESERVED_EDGE_KEYS = frozenset({_META_KEY, _SRC_KEY, _TGT_KEY, _CONF_KEY})


# ── Type-conversion helpers ───────────────────────────────────────────────────


def _entity_to_node_spec(entity: Entity) -> NodeSpec:
    """Build a ``NodeSpec`` from an ``Entity``."""
    properties: dict[str, Any] = {
        _NAME_KEY: entity.name,
        _TYPE_KEY: str(entity.type),
        **entity.properties,
    }
    if entity.metadata:
        properties[_META_KEY] = entity.metadata
    return NodeSpec(
        labels=(str(entity.type),),
        properties=properties,
        id=entity.name.lower(),
    )


def _node_to_entity(node: GraphNode) -> Entity:
    """Reconstruct an ``Entity`` from a ``GraphNode``."""
    name: str = node.properties.get(_NAME_KEY, node.id)
    raw_type: str = (
        node.properties.get(_TYPE_KEY)
        or (node.labels[0] if node.labels else None)
        or str(EntityType.OTHER)
    )
    try:
        entity_type: EntityType | str = EntityType(raw_type)
    except ValueError:
        entity_type = raw_type

    extra = {k: v for k, v in node.properties.items() if k not in _RESERVED_NODE_KEYS}
    metadata: dict[str, Any] = node.properties.get(_META_KEY, {})
    return Entity(
        name=name,
        type=entity_type,
        properties=extra,
        metadata=metadata,
    )


def _relationship_to_edge_spec(rel: Relationship) -> EdgeSpec:
    """Build an ``EdgeSpec`` from a ``Relationship``."""
    properties: dict[str, Any] = {
        _CONF_KEY: rel.confidence,
        _SRC_KEY: rel.source,
        _TGT_KEY: rel.target,
        **rel.properties,
    }
    if rel.metadata:
        properties[_META_KEY] = rel.metadata
    return EdgeSpec(
        source_id=rel.source.lower(),
        target_id=rel.target.lower(),
        type=str(rel.type),
        properties=properties,
    )


def _edge_to_relationship(edge: GraphEdge) -> Relationship:
    """Reconstruct a ``Relationship`` from a ``GraphEdge``."""
    source: str = edge.properties.get(_SRC_KEY, edge.source_id)
    target: str = edge.properties.get(_TGT_KEY, edge.target_id)
    confidence: float = edge.properties.get(_CONF_KEY, 1.0)
    raw_type: str = edge.type
    try:
        rel_type: RelationshipType | str = RelationshipType(raw_type)
    except ValueError:
        rel_type = raw_type

    extra = {k: v for k, v in edge.properties.items() if k not in _RESERVED_EDGE_KEYS}
    metadata: dict[str, Any] = edge.properties.get(_META_KEY, {})
    return Relationship(
        source=source,
        target=target,
        type=rel_type,
        confidence=confidence,
        properties=extra,
        metadata=metadata,
    )


def _infra_path_to_rag_path(path: InfraGraphPath) -> GraphPath:
    """Convert an infrastructure ``GraphPath`` to a RAG ``GraphPath``."""
    entity_names = [node.properties.get(_NAME_KEY, node.id) for node in path.nodes]
    rels = [_edge_to_relationship(e) for e in path.edges]
    confidence_sum = sum(r.confidence for r in rels)
    score = confidence_sum / len(rels) if rels else 1.0
    return GraphPath(
        entities=entity_names,
        relationships=rels,
        length=path.length,
        score=score,
    )


# ── Adapter ───────────────────────────────────────────────────────────────────


class GraphStoreAdapter:
    """``KnowledgeGraph``-compatible adapter backed by a ``GraphProtocol``.

    Entities are stored as nodes (label = entity type, id = name.lower()).
    Relationships are stored as directed edges (type = relationship type).
    Confidence and original name strings are persisted in edge properties so
    round-tripping is lossless.

    Args:
        graph: A ``GraphProtocol`` instance from ``lexigram-graph`` (or any
               other backend implementing the contract).
    """

    def __init__(self, graph: GraphProtocol) -> None:
        """Initialise the adapter with a graph protocol instance."""
        self._graph = graph

    # ── Entity mutations ──────────────────────────────────────────

    async def add_entity(self, entity: Entity) -> None:
        """Add or upsert an entity as a graph node."""
        spec = _entity_to_node_spec(entity)
        existing = await self._graph.get_node(entity.name.lower())
        if existing is None:
            await self._graph.bulk_create_nodes([spec])
        else:
            # Upsert: merge properties
            await self._graph.update_node(
                entity.name.lower(),
                properties={
                    _NAME_KEY: entity.name,
                    _TYPE_KEY: str(entity.type),
                    **entity.properties,
                    **({_META_KEY: entity.metadata} if entity.metadata else {}),
                },
                merge=True,
            )

    async def add_entities(self, entities: list[Entity]) -> None:
        """Add or upsert multiple entities."""
        for entity in entities:
            await self.add_entity(entity)

    async def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship as a directed edge between two nodes."""
        spec = _relationship_to_edge_spec(relationship)
        try:
            await self._graph.create_edge(
                source_id=spec.source_id,
                target_id=spec.target_id,
                edge_type=spec.type,
                properties=spec.properties,
            )
        except Exception as exc:  # noqa: BLE001 — graph adapter relationship; skipped if nodes don't exist; log and continue
            # Nodes may not exist yet — surface as a warning and skip.
            logger.warning(
                "graph_adapter_relationship_skipped",
                source=relationship.source,
                target=relationship.target,
                error=str(exc),
            )

    async def add_relationships(self, relationships: list[Relationship]) -> None:
        """Add multiple relationships."""
        for rel in relationships:
            await self.add_relationship(rel)

    # ── Entity queries ────────────────────────────────────────────

    async def get_entity(self, name: str) -> Entity | None:
        """Retrieve an entity by name. Returns ``None`` if not found."""
        node = await self._graph.get_node(name.lower())
        if node is None:
            return None
        return _node_to_entity(node)

    async def get_all_entities(self) -> list[Entity]:
        """Return all entities in the graph."""
        nodes = await self._graph.find_nodes(limit=10_000)
        return [_node_to_entity(n) for n in nodes]

    async def get_entities_by_type(
        self,
        entity_type: EntityType | str,
    ) -> list[Entity]:
        """Return all entities of the given type."""
        label = str(entity_type)
        nodes = await self._graph.find_nodes(labels=[label], limit=10_000)
        return [_node_to_entity(n) for n in nodes]

    # ── Relationship queries ──────────────────────────────────────

    async def get_all_relationships(self) -> list[Relationship]:
        """Return all relationships in the graph."""
        nodes = await self._graph.find_nodes(limit=10_000)
        rels: list[Relationship] = []
        seen: set[str] = set()
        for node in nodes:
            edges = await self._graph.get_edges(
                node.id,
                direction=EdgeDirection.OUTGOING,
                limit=10_000,
            )
            for edge in edges:
                if edge.id not in seen:
                    seen.add(edge.id)
                    rels.append(_edge_to_relationship(edge))
        return rels

    async def get_neighbors(
        self,
        entity_name: str,
        direction: str = "outgoing",
    ) -> list[Entity]:
        """Return neighbouring entities reachable in one hop."""
        dir_map: dict[str, EdgeDirection] = {
            "outgoing": EdgeDirection.OUTGOING,
            "incoming": EdgeDirection.INCOMING,
            "both": EdgeDirection.BOTH,
        }
        infra_dir = dir_map.get(direction, EdgeDirection.BOTH)
        nodes = await self._graph.neighbors(
            node_id=entity_name.lower(),
            depth=1,
            direction=infra_dir,
        )
        return [_node_to_entity(n) for n in nodes]

    async def get_relationships(
        self,
        entity_name: str,
        direction: str = "outgoing",
    ) -> list[Relationship]:
        """Return relationships attached to the named entity."""
        dir_map: dict[str, EdgeDirection] = {
            "outgoing": EdgeDirection.OUTGOING,
            "incoming": EdgeDirection.INCOMING,
            "both": EdgeDirection.BOTH,
        }
        infra_dir = dir_map.get(direction, EdgeDirection.BOTH)
        edges = await self._graph.get_edges(
            node_id=entity_name.lower(),
            direction=infra_dir,
            limit=10_000,
        )
        return [_edge_to_relationship(e) for e in edges]

    # ── Path queries ──────────────────────────────────────────────

    async def find_path(
        self,
        source: str,
        target: str,
        max_depth: int = 5,
        relationship_types: list[RelationshipType | str] | None = None,
    ) -> GraphPath | None:
        """Find the shortest path between two entities."""
        edge_types = (
            [str(t) for t in relationship_types] if relationship_types else None
        )
        infra_path = await self._graph.shortest_path(
            from_id=source.lower(),
            to_id=target.lower(),
            max_depth=max_depth,
            edge_types=edge_types,
            direction=EdgeDirection.BOTH,
        )
        if infra_path is None:
            return None
        return _infra_path_to_rag_path(infra_path)

    async def find_all_paths(
        self,
        source: str,
        target: str,
        max_depth: int = 5,
        max_paths: int = 10,
    ) -> list[GraphPath]:
        """Find up to ``max_paths`` paths between two entities via traversal."""
        start = StartSpec(node_ids=(source.lower(),))
        steps = (
            TraversalStep(
                direction=EdgeDirection.BOTH,
                min_depth=1,
                max_depth=max_depth,
            ),
        )
        query = TraversalQuery(
            start=start,
            steps=steps,
            limit=max_paths,
            unique_nodes=True,
        )
        all_paths = await self._graph.traverse(query)
        # Filter to only paths that end at the target node.
        target_id = target.lower()
        matching = [p for p in all_paths if p.end_node.id == target_id]
        rag_paths = [_infra_path_to_rag_path(p) for p in matching[:max_paths]]
        rag_paths.sort(key=lambda p: p.score, reverse=True)
        return rag_paths

    async def query_subgraph(
        self,
        entity_name: str,
        depth: int = 2,
    ) -> tuple[list[Entity], list[Relationship]]:
        """Return all entities and relationships within ``depth`` hops."""
        start_id = entity_name.lower()
        # Collect reachable nodes at each depth level.
        entities_found: dict[str, Entity] = {}
        rels_found: dict[str, Relationship] = {}

        root = await self._graph.get_node(start_id)
        if root is None:
            return [], []
        entities_found[start_id] = _node_to_entity(root)

        current_layer: set[str] = {start_id}
        for _ in range(depth):
            next_layer: set[str] = set()
            for nid in current_layer:
                edges = await self._graph.get_edges(
                    nid,
                    direction=EdgeDirection.BOTH,
                    limit=10_000,
                )
                for edge in edges:
                    neighbor_id = (
                        edge.target_id if edge.source_id == nid else edge.source_id
                    )
                    if edge.id not in rels_found:
                        rels_found[edge.id] = _edge_to_relationship(edge)
                    if neighbor_id not in entities_found:
                        neighbor = await self._graph.get_node(neighbor_id)
                        if neighbor is not None:
                            entities_found[neighbor_id] = _node_to_entity(neighbor)
                            next_layer.add(neighbor_id)
            current_layer = next_layer

        return list(entities_found.values()), list(rels_found.values())

    # ── Stats ─────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        """Return basic graph statistics."""
        node_count = await self._graph.count_nodes()
        edge_count = await self._graph.count_edges()
        labels = await self._graph.get_labels()
        edge_types = await self._graph.get_edge_types()
        return {
            "total_entities": node_count,
            "total_relationships": edge_count,
            "entity_types": labels,
            "relationship_types": edge_types,
        }

    def __len__(self) -> int:
        """Return entity count (synchronous best-effort — may be stale)."""
        # Not async-safe; kept for protocol compatibility.
        return 0

    def __repr__(self) -> str:
        return f"GraphStoreAdapter(graph={self._graph!r})"
