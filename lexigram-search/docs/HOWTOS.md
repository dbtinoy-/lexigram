---
title: lexigram-search How-Tos
description: Task-oriented recipes for common search operations.
---

## How do I index a single document?

```python
from lexigram.contracts.search import SearchEngineProtocol

engine = await container.resolve(SearchEngineProtocol)
await engine.index_document("doc-42", {"title": "My Document", "tags": ["guide"]})
```

## How do I bulk-index many documents?

```python
engine = await container.resolve(SearchEngineProtocol)
documents = [
    ("doc-1", {"title": "First", "content": "..."}),
    ("doc-2", {"title": "Second", "content": "..."}),
    ("doc-3", {"title": "Third", "content": "..."}),
]
await engine.index_many(documents)
```

Prefer `index_many()` over N individual `index_document()` calls for throughput.

## How do I search with pagination and filters?

```python
from lexigram.contracts.search import SearchEngineProtocol

engine = await container.resolve(SearchEngineProtocol)
result = await engine.search(
    "query text",
    filters={"status": "published", "category": "guide"},
    sort=[{"created_at": "desc"}],
    limit=20,
    offset=40,
)
print(f"Page 3 of {result.total} results")
for hit in result.results:
    print(hit.data["title"], hit.score)
```

## How do I use filtersets for complex filtering?

```python
from lexigram.search import FilterSet, FilterCondition, FilterOperator

filters = FilterSet(
    conditions=[
        FilterCondition(field="status", operator=FilterOperator.EQ, value="active"),
        FilterCondition(field="price", operator=FilterOperator.GTE, value=10.0),
    ]
)
# Pass to a FilterSetTranslator for your backend
from lexigram.search import FilterSetTranslator

translator = FilterSetTranslator()
query_filters = translator.translate(filters)
```

## How do I set up a federated search across multiple backends?

```python
from lexigram.search import FederatedSearchEngine

# Two backends resolved from the container
primary = await container.resolve(SearchEngineProtocol, name="primary")
secondary = await container.resolve(SearchEngineProtocol, name="secondary")

federated = FederatedSearchEngine(engines=[primary, secondary])
results = await federated.search("query", merge_strategy="rank")
```

## How do I validate and sanitize user search input?

```python
from lexigram.search import (
    validate_search_query,
    validate_search_filters,
    sanitize_search_query,
    validate_index_name,
)

# Validate — raises SearchValidationError
validate_search_query(user_input)
validate_index_name("my-index")

# Sanitize — returns cleaned version
clean = sanitize_search_query(raw_input)
```

## How do I implement custom search analytics?

```python
from lexigram.search import SearchAnalyticsRecorder

class MyAnalyticsRecorder(SearchAnalyticsRecorder):
    async def record_search(self, query, filters, result_count, user_id=None, session_id=None):
        await self.db.log_search(user_id, query, result_count)

# Register with the provider
provider = SearchProvider.with_meilisearch()
provider.analytics = MyAnalyticsRecorder(db=...)
```

## How do I connect a PostgreSQL FTS backend?

```python
from lexigram.search.config import (
    SearchConfig,
    BackendType,
    PostgresSearchConfig,
)

config = SearchConfig(
    backend_type=BackendType.POSTGRES,
    postgres=PostgresSearchConfig(
        connection_string="postgresql://user:pass@localhost/mydb",
        text_search_config="english",
        enable_trigram=True,
    ),
)
app.add_provider(SearchProvider.configure(config))
```

The provider resolves `DatabaseProviderProtocol` during `boot()` to wire the real backend.
