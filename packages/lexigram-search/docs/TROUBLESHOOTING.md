---
title: lexigram-search Troubleshooting
description: Common errors, causes, and fixes.
---

## Backend unreachable at startup

**Error:** `RuntimeError: Search backend MeiliSearchBackend is unhealthy at startup`

**Cause:** The search backend server is not running or not reachable at the configured URL.

**Fix:** Start the backend service or verify the connection URL:

```bash
# Check if MeiliSearch is running
curl http://localhost:7700/health
# Expected: {"status": "available"}

# For Elasticsearch
curl http://localhost:9200/_cluster/health
```

If running in Docker, verify network configuration and port mapping.

## Backend not available

**Error:** `BackendError` (code `LEX_ERR_SEARCH_003`)

**Cause:** The search backend is configured but the driver dependency is not installed.

**Fix:** Install the required extra:

```bash
uv add "lexigram-search[meilisearch]"
# or
uv add "lexigram-search[elasticsearch]"
# or
uv add "lexigram-search[postgres]"
```

## Invalid backend type

**Error:** `ValueError: Unsupported backend type: <type>`

**Cause:** `SearchConfig.backend_type` is set to a string that doesn't match any `BackendType` enum member.

**Fix:** Use a valid `BackendType`:

```python
from lexigram.search.config import BackendType

# Valid options
BackendType.MEILISEARCH
BackendType.ELASTICSEARCH
BackendType.OPENSEARCH
BackendType.TYPESENSE
BackendType.POSTGRES
BackendType.MYSQL
BackendType.SQLITE
BackendType.MONGODB
BackendType.MEMORY
```

## Query rejected (bad input)

**Error:** `SearchValidationError` (code `LEX_ERR_SEARCH_004`)

**Cause:** The search query failed validation — too long, contains prohibited characters, or invalid structure.

**Fix:** Use the validation helpers before querying:

```python
from lexigram.search import validate_search_query, sanitize_search_query

# Check before sending to backend
try:
    validate_search_query(user_input)
except SearchValidationError as e:
    return {"error": str(e)}

# Or sanitize silently
safe_query = sanitize_search_query(user_input)
```

## Index operation failed

**Error:** `SearchIndexError` (code `LEX_ERR_SEARCH_009`)

**Cause:** The search backend rejected an index operation — document too large, invalid schema, or index does not exist.

**Fix:** Verify the index exists before indexing:

```python
from lexigram.contracts.search import IndexManagerProtocol

manager = await container.resolve(IndexManagerProtocol)
if not await manager.index_exists("my_index"):
    await manager.create_index("my_index", {"fields": ["title", "content"]})
```

## Multi-backend: database not found

**Error:** `KeyError: DatabaseProviderProtocol not registered`

**Cause:** A DB-backed backend (POSTGRES, MYSQL) is configured but `lexigram-sql` is not installed or `DatabaseProvider` is not registered.

**Fix:** Install `lexigram-sql` and add its provider:

```bash
uv add lexigram-sql
```

```python
from lexigram.sql import DatabaseProvider

app.add_provider(DatabaseProvider.configure(...))
```

## Search returns no results

**Cause 1:** Documents were never indexed. Check that `index_document()` or `index_many()` was called.

**Cause 2:** The query is too strict. Try with `SearchStrategy.FUZZY`:

```python
from lexigram.search.types import SearchStrategy

# In SearchConfig
config = SearchConfig(
    query=QueryConfig(strategy=SearchStrategy.FUZZY, fuzzy_threshold=0.6),
)
```

**Cause 3:** Filters exclude everything. Remove filters one at a time to isolate the issue.

## Connection refused

**Error:** `ConnectionError` or `OSError` wrapping "Connection refused"

**Cause:** The search backend server is not running on the configured host/port.

**Fix:** Check the backend service status and verify the URL in your config.
