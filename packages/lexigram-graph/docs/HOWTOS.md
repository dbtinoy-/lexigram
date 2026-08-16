---
title: lexigram-graph How-Tos
description: Task-oriented recipes for common graph operations.
---

## Wire a Graph Store in Your App

```python
from lexigram import Application
from lexigram.graph import GraphModule, GraphConfig

app = Application(name="myapp")
app.add_module(
    GraphModule.configure(GraphConfig(backend="memory"))
)
await app.start()
```

For Neo4j:

```python
app.add_module(
    GraphModule.configure(GraphConfig(backend="neo4j"))
)
```

## Create Nodes and Edges

```python
from lexigram.contracts.data.graph import GraphProtocol, GraphStoreProtocol


class WikiService:
    def __init__(self, store: GraphStoreProtocol) -> None:
        self.graph = await store.get_graph()

    async def add_article(self, article_id: str, title: str) -> None:
        await self.graph.create_node(
            ["Article"],
            {"title": title, "url": f"/wiki/{article_id}"},
            node_id=article_id,
        )

    async def link_articles(
        self, source: str, target: str, label: str
    ) -> None:
        await self.graph.create_edge(
            source, target, "REFERENCES",
            {"label": label},
        )

    async def get_related(self, article_id: str) -> list[GraphNode]:
        return await self.graph.neighbors(
            article_id, depth=1, direction="BOTH",
        )
```

## Find the Shortest Path Between Nodes

```python
from lexigram.contracts.data.graph import EdgeDirection


class RouteService:
    def __init__(self, graph: GraphProtocol) -> None:
        self.graph = graph

    async def find_connection(
        self, person_a: str, person_b: str, max_depth: int = 6,
    ) -> GraphPath | None:
        """Find shortest connection path (e.g., LinkedIn-style)."""
        return await self.graph.shortest_path(
            person_a, person_b,
            max_depth=max_depth,
            direction=EdgeDirection.BOTH,
        )
```

## Use Raw Cypher Queries

```python
# Neo4j passthrough for complex queries
result = await graph.query(
    """
    MATCH (u:User)-[:PURCHASED]->(p:Product)
    WHERE u.id = $user_id
    RETURN p.title, count(*) AS purchase_count
    ORDER BY purchase_count DESC
    LIMIT 10
    """,
    parameters={"user_id": "user-42"},
)
for row in result:
    print(f"{row['p.title']}: {row['purchase_count']} purchases")
```

## Bulk Import Data

```python
from lexigram.contracts.data.graph import NodeSpec, EdgeSpec


async def import_catalog(graph: GraphProtocol) -> None:
    # Bulk create nodes
    nodes = [
        NodeSpec(labels=["Category"], properties={"name": "Electronics"}),
        NodeSpec(labels=["Category"], properties={"name": "Books"}),
        NodeSpec(labels=["Product"], properties={
            "sku": "E-001", "name": "Headphones", "price": 99.99,
        }),
        NodeSpec(labels=["Product"], properties={
            "sku": "B-001", "name": "Python 101", "price": 29.99,
        }),
    ]
    node_result = await graph.bulk_create_nodes(nodes)
    print(f"Created {node_result.count} nodes")

    # Bulk create edges
    edges = [
        EdgeSpec(
            source_id=node_result.node_ids[0],
            target_id=node_result.node_ids[2],
            edge_type="CONTAINS",
        ),
        EdgeSpec(
            source_id=node_result.node_ids[1],
            target_id=node_result.node_ids[3],
            edge_type="CONTAINS",
        ),
    ]
    edge_result = await graph.bulk_create_edges(edges)
    print(f"Created {edge_result.count} edges")
```

## Manage Schema (Neo4j)

```python
from lexigram.contracts.data.graph import (
    IndexSpec, ConstraintSpec,
)


class SchemaService:
    def __init__(self, graph: GraphProtocol) -> None:
        self.graph = graph

    async def ensure_schema(self) -> None:
        # Unique constraint on User.email
        await self.graph.create_constraint(
            ConstraintSpec(
                label="User",
                property="email",
                type="unique",
            )
        )
        # Index on Product(category, price)
        await self.graph.create_index(
            IndexSpec(
                label="Product",
                properties=["category", "price"],
            )
        )
```

## Test with the In-Memory Backend

```python
from lexigram import Application
from lexigram.graph import GraphModule


# GraphModule.stub() uses the in-memory backend
app = Application(name="test", testing=True)
app.add_module(GraphModule.stub())
await app.start()

# No Neo4j required — everything runs in-process
```

## Handle a Graph Query Failure

```python
from lexigram.graph.exceptions import GraphQueryError, GraphConnectionError


class SafeGraphQueryService:
    def __init__(self, graph: GraphProtocol) -> None:
        self.graph = graph

    async def find_user_safe(self, user_id: str) -> GraphNode | None:
        try:
            return await self.graph.get_node(user_id)
        except GraphConnectionError:
            logger.error("graph_unavailable")
            return None
```
