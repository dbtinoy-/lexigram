---
title: lexigram-graph Troubleshooting
description: Common errors, their causes, and fixes.
---

## Connection Refused (Neo4j)

**Error:** `GraphConnectionError` — "Failed to connect to the graph store"

**Cause:** Neo4j isn't running, the BOLT URI is wrong, or a firewall is blocking port 7687.

**Fix:**
- Verify Neo4j is running: `cypher-shell "RETURN 1"`.
- Check `graph.neo4j.uri` or `LEX_GRAPH__NEO4J__URI`.
- For Docker: `docker compose up neo4j` and use `bolt://localhost:7687`.

## In-Memory Backend in Production

**Error:** `ConfigIssue` with severity `error` — "In-memory graph store used in production"

**Cause:** `graph.backend` is set to `"memory"` and `Environment` is production.

**Fix:**
```yaml
graph:
  backend: neo4j  # switch to persistent backend
  neo4j:
    uri: bolt://...
```

## Neo4j Password Missing

**Error:** `ConfigIssue` with severity `error` — "Neo4j password missing in production"

**Cause:** `graph.neo4j.password` is empty and the environment is production.

**Fix:**
```bash
export LEX_GRAPH__NEO4J__PASSWORD="your-secure-password"
```

## Graph Not Found

**Error:** `GraphNotFoundError("Graph database 'X' not found")`

**Cause:** `store.get_graph("X")` was called before `store.create_graph("X")`, or the name is misspelled.

**Fix:**
```python
await store.create_graph("X")  # create first
graph = await store.get_graph("X")
```

## Graph Already Exists

**Error:** `GraphAlreadyExistsError("Graph database 'X' already exists")`

**Cause:** `store.create_graph("X")` was called for a graph that already exists.

**Fix:**
- Call `create_graph` only once on first boot.
- Use `try/except GraphAlreadyExistsError` to ignore if idempotent.

## Node Not Found

**Error:** `GraphNodeNotFoundError("Node 'X' not found")` or `get_node` returns `None`

**Cause:** A node with the given ID does not exist.

**Fix:**
- Check the node ID is correct.
- Verify it was created: `await graph.get_node(node_id)` returns `None` if not found.

## Edge Not Found

**Error:** `GraphEdgeNotFoundError("Edge 'X' not found")`

**Cause:** The edge ID is wrong or the edge was deleted.

**Fix:**
- List edges for the source/target node: `await graph.get_edges(node_id)`.
- Verify the edge ID matches.

## Detach Required When Deleting Node

**Error:** `DetachRequiredError("Node 'X' has N edges. Use detach=True to delete them.")`

**Cause:** `delete_node(node_id, detach=False)` or default, but the node has edges.

**Fix:**
```python
await graph.delete_node(node_id, detach=True)  # deletes edges too
```

## Unsupported Backend

**Error:** `ValueError("Unsupported graph backend: X")`

**Cause:** `config.backend` is set to something other than `"memory"` or `"neo4j"`.

**Fix:**
```yaml
graph:
  backend: neo4j  # or "memory"
```

## Cypher Compilation Failed

**Error:** `CypherCompilationError("Cypher compilation failed: ...")`

**Cause:** A traversal query could not be compiled to Cypher for the Neo4j backend.

**Fix:**
- Check the traversal query parameters are valid.
- Use `graph.query()` with raw Cypher if you need full control.
- Verify the `TraversalQuery` structure matches the expected schema.
