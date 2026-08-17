"""Core knowledge graph implementation (migrated from legacy single-file module).

This module contains the canonical, package-local implementations and should be
imported from `lexigram.ai.rag.knowledge_graph`.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from lexigram.ai.rag.knowledge_graph.extractors import (
    EntityExtractor,
    RelationshipExtractor,
)
from lexigram.ai.rag.knowledge_graph.types import (
    Entity,
    EntityType,
    GraphPath,
    Relationship,
    RelationshipType,
)

if TYPE_CHECKING:
    from lexigram.contracts.ai import (
        DocumentVectorStoreProtocol,
        LLMClientProtocol,
    )


class KnowledgeGraph:
    """In-memory knowledge graph for storing and querying entities and relationships."""

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, list[Relationship]] = defaultdict(list)
        self._reverse_relationships: dict[str, list[Relationship]] = defaultdict(list)
        self._entity_index: dict[EntityType, set[str]] = defaultdict(set)
        self._created_at = datetime.now(UTC)
        self._updated_at = datetime.now(UTC)

    async def add_entity(self, entity: Entity) -> None:
        key = entity.name.lower()
        self._entities[key] = entity
        self._entity_index[EntityType(entity.type)].add(key)
        self._updated_at = datetime.now(UTC)

    async def add_entities(self, entities: list[Entity]) -> None:
        for entity in entities:
            await self.add_entity(entity)

    async def add_relationship(self, relationship: Relationship) -> None:
        source_key = relationship.source.lower()
        target_key = relationship.target.lower()

        self._relationships[source_key].append(relationship)
        self._reverse_relationships[target_key].append(relationship)
        self._updated_at = datetime.now(UTC)

    async def add_relationships(self, relationships: list[Relationship]) -> None:
        for relationship in relationships:
            await self.add_relationship(relationship)

    async def get_entity(self, name: str) -> Entity | None:
        return self._entities.get(name.lower())

    async def get_all_entities(self) -> list[Entity]:
        """Get all entities in the knowledge graph."""
        return list(self._entities.values())

    async def get_all_relationships(self) -> list[Relationship]:
        """Get all relationships in the knowledge graph."""
        all_relationships = []
        for rels in self._relationships.values():
            all_relationships.extend(rels)
        return all_relationships

    async def get_entities_by_type(self, entity_type: EntityType | str) -> list[Entity]:
        entity_type = EntityType(entity_type)
        names = self._entity_index.get(entity_type, set())
        return [self._entities[name] for name in names if name in self._entities]

    async def get_neighbors(
        self,
        entity_name: str,
        direction: str = "outgoing",
    ) -> list[Entity]:
        key = entity_name.lower()
        neighbors = set()

        if direction in ("outgoing", "both"):
            for rel in self._relationships.get(key, []):
                target = await self.get_entity(rel.target)
                if target:
                    neighbors.add(target)

        if direction in ("incoming", "both"):
            for rel in self._reverse_relationships.get(key, []):
                source = await self.get_entity(rel.source)
                if source:
                    neighbors.add(source)

        return list(neighbors)

    async def get_relationships(
        self,
        entity_name: str,
        direction: str = "outgoing",
    ) -> list[Relationship]:
        key = entity_name.lower()
        rels = []

        if direction in ("outgoing", "both"):
            rels.extend(self._relationships.get(key, []))

        if direction in ("incoming", "both"):
            rels.extend(self._reverse_relationships.get(key, []))

        return rels

    async def find_path(
        self,
        source: str,
        target: str,
        max_depth: int = 5,
        relationship_types: list[RelationshipType | str] | None = None,
    ) -> GraphPath | None:
        source_key = source.lower()
        target_key = target.lower()

        if source_key not in self._entities or target_key not in self._entities:
            return None

        queue: deque[tuple[str, list[Relationship]]] = deque([(source_key, [])])
        visited = {source_key}

        while queue:
            current, path_rels = queue.popleft()

            if len(path_rels) >= max_depth:
                continue

            if current == target_key:
                entities = [source]
                for rel in path_rels:
                    entities.append(rel.target)

                return GraphPath(
                    entities=entities,
                    relationships=path_rels,
                    length=len(path_rels),
                    score=(
                        sum(r.confidence for r in path_rels) / len(path_rels)
                        if path_rels
                        else 1.0
                    ),
                )

            for rel in self._relationships.get(current, []):
                if relationship_types and rel.type not in relationship_types:
                    continue

                neighbor = rel.target.lower()
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, [*path_rels, rel]))

        return None

    async def find_all_paths(
        self,
        source: str,
        target: str,
        max_depth: int = 5,
        max_paths: int = 10,
    ) -> list[GraphPath]:
        source_key = source.lower()
        target_key = target.lower()

        if source_key not in self._entities or target_key not in self._entities:
            return []

        paths: list[GraphPath] = []

        def dfs(current: str, path_rels: list[Relationship], visited: set[str]) -> Any:
            if len(paths) >= max_paths:
                return

            if len(path_rels) >= max_depth:
                return

            if current == target_key and path_rels:
                entities = [source]
                for rel in path_rels:
                    entities.append(rel.target)

                path = GraphPath(
                    entities=entities,
                    relationships=path_rels,
                    length=len(path_rels),
                    score=sum(r.confidence for r in path_rels) / len(path_rels),
                )
                paths.append(path)
                return

            for rel in self._relationships.get(current, []):
                neighbor = rel.target.lower()
                if neighbor not in visited:
                    visited.add(neighbor)
                    dfs(neighbor, [*path_rels, rel], visited)
                    visited.remove(neighbor)

        dfs(source_key, [], {source_key})

        paths.sort(key=lambda p: p.score, reverse=True)
        return paths

    async def query_subgraph(
        self,
        entity_name: str,
        depth: int = 2,
    ) -> tuple[list[Entity], list[Relationship]]:
        key = entity_name.lower()
        if key not in self._entities:
            return [], []

        entities_found = {key}
        relationships_found = []

        current_level = {key}
        for _ in range(depth):
            next_level = set()

            for entity_key in current_level:
                for rel in self._relationships.get(entity_key, []):
                    relationships_found.append(rel)
                    target = rel.target.lower()
                    entities_found.add(target)
                    next_level.add(target)

                for rel in self._reverse_relationships.get(entity_key, []):
                    relationships_found.append(rel)
                    source = rel.source.lower()
                    entities_found.add(source)
                    next_level.add(source)

            current_level = next_level

        entities = [
            self._entities[name] for name in entities_found if name in self._entities
        ]

        return entities, relationships_found

    def get_stats(self) -> dict[str, Any]:
        total_rels = sum(len(rels) for rels in self._relationships.values())

        entity_counts = {
            str(etype): len(names) for etype, names in self._entity_index.items()
        }

        rel_counts: dict[str, int] = defaultdict(int)
        for rels in self._relationships.values():
            for rel in rels:
                rel_counts[str(rel.type)] += 1

        return {
            "total_entities": len(self._entities),
            "total_relationships": total_rels,
            "entity_counts": entity_counts,
            "relationship_counts": dict(rel_counts),
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    def __len__(self) -> int:
        return len(self._entities)

    def __repr__(self) -> str:
        return f"KnowledgeGraph(entities={len(self._entities)}, relationships={sum(len(r) for r in self._relationships.values())})"


class KnowledgeGraphBuilder:
    """Builder for constructing knowledge graphs from text/documents."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        entity_types: list[EntityType | str] | None = None,
        relationship_types: list[RelationshipType | str] | None = None,
        min_confidence: float = 0.5,
    ):
        self.entity_extractor = EntityExtractor(
            llm_client=llm_client,
            entity_types=entity_types,
            min_confidence=min_confidence,
        )
        self.relationship_extractor = RelationshipExtractor(
            llm_client=llm_client,
            relationship_types=relationship_types,
            min_confidence=min_confidence,
        )

    async def build_from_text(self, text: str) -> KnowledgeGraph:
        try:
            import importlib

            public_kg = getattr(
                importlib.import_module("lexigram.ai.rag.knowledge_graph"),
                "KnowledgeGraph",
                None,
            )
        except (ImportError, ModuleNotFoundError, AttributeError):
            public_kg = None

        kg = public_kg() if public_kg is not None else KnowledgeGraph()

        entities = await self.entity_extractor.extract(text)
        await kg.add_entities(entities)

        relationships = await self.relationship_extractor.extract(text, entities)
        await kg.add_relationships(relationships)

        return kg

    async def build_from_documents(
        self,
        documents: list[str],
        merge: bool = True,
    ) -> KnowledgeGraph | list[KnowledgeGraph]:
        if merge:
            kg = KnowledgeGraph()
            for doc in documents:
                doc_kg = await self.build_from_text(doc)

                for entity in await doc_kg.get_all_entities():
                    await kg.add_entity(entity)

                for rel in await doc_kg.get_all_relationships():
                    await kg.add_relationship(rel)

            try:
                import importlib

                _pkg_mod = importlib.import_module("lexigram.ai.rag.knowledge_graph")
                public_kg = getattr(_pkg_mod, "KnowledgeGraph", None)
                if public_kg and not isinstance(kg, public_kg):
                    new_kg = public_kg()
                    for entity in await kg.get_all_entities():
                        await new_kg.add_entity(entity)
                    for rel in await kg.get_all_relationships():
                        await new_kg.add_relationship(rel)
                    kg = new_kg
            except (ImportError, ModuleNotFoundError, AttributeError):
                pass

            return kg
        graphs = []
        for doc in documents:
            kg = await self.build_from_text(doc)
            graphs.append(kg)

        try:
            import importlib

            _pkg_mod = importlib.import_module("lexigram.ai.rag.knowledge_graph")
            public_kg = getattr(_pkg_mod, "KnowledgeGraph", None)
            if public_kg:
                normalized: list[KnowledgeGraph] = []
                for g in graphs:
                    if isinstance(g, public_kg):
                        normalized.append(g)
                    else:
                        new_kg = public_kg()
                        for entity in await g.get_all_entities():
                            await new_kg.add_entity(entity)
                        for rel in await g.get_all_relationships():
                            await new_kg.add_relationship(rel)
                        normalized.append(new_kg)
                return normalized
        except (ImportError, ModuleNotFoundError, AttributeError):
            pass

        return graphs


class GraphRAGIntegration:
    """Integrates knowledge graph with RAG pipeline for enhanced retrieval."""

    def __init__(
        self,
        knowledge_graph: KnowledgeGraph,
        vector_store: DocumentVectorStoreProtocol,
        llm_client: LLMClientProtocol,
    ):
        self.kg = knowledge_graph
        self.vector_store = vector_store
        self.llm_client = llm_client

    async def expand_query_with_graph(
        self,
        query: str,
        max_expansions: int = 5,
    ) -> list[str]:
        entities = await EntityExtractor(self.llm_client).extract(query)

        queries = [query]

        for entity in entities[:3]:
            neighbors = await self.kg.get_neighbors(entity.name, direction="both")

            for neighbor in neighbors[: max_expansions - len(queries)]:
                expanded = f"{query} {neighbor.name}"
                queries.append(expanded)

                if len(queries) >= max_expansions:
                    break

            if len(queries) >= max_expansions:
                break

        return queries

    async def retrieve_with_graph(
        self,
        query: str,
        top_k: int = 5,
        expand: bool = True,
    ) -> list[Any]:
        queries = [query]

        if expand:
            queries = await self.expand_query_with_graph(query, max_expansions=3)

        all_results = []
        for q in queries:
            search_result = await self.vector_store.search(q, top_k=top_k)  # type: ignore[arg-type]
            all_results.extend(search_result.unwrap_or([]))

        seen = set()
        unique_results = []
        for result in all_results:
            doc_id = getattr(result, "id", hash(getattr(result, "text", "")))
            if doc_id not in seen:
                seen.add(doc_id)
                unique_results.append(result)

        return unique_results[:top_k]
