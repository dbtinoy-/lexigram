---
title: lexigram-search Guide
description: Mental model, core concepts, and end-to-end usage of full-text search.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `elasticsearch` | Recommended | Elasticsearch backend |
| `meilisearch` | Optional | Meilisearch backend |
| `typesense` | Optional | Typesense backend |

## Problem

Your application needs full-text search — fast, typo-tolerant, faceted — across entities. You don't want to couple your domain code to a specific search vendor (MeiliSearch, Elasticsearch, Typesense) or hand-write SQL `LIKE` queries.

`lexigram-search` wraps any search backend behind `SearchEngineProtocol` and manages the provider lifecycle, index management, and result mapping.

## Mental Model

```
Domain Entity  →  SearchEngineProtocol  →  Backend (MeiliSearch / ES / SQL / …)
                       ↕
               IndexManagerProtocol
                       ↕
               SearchAnalyticsProtocol
```

Your domain code speaks to protocols. The provider selects and wires the backend. Swap backends without touching business logic.

## Core Concepts

### SearchEngineProtocol

The primary contract. Every backend implements `search()`, `index_document()`, `index_many()`, `delete_document()`, and `health_check()`:

```python
from lexigram.contracts.search import SearchEngineProtocol

class MyService:
    def __init__(self, search: SearchEngineProtocol) -> None:
        self.search = search
```

### SearchProvider

The provider that registers the search backend in the DI container. Supports single-backend and multi-backend modes:

```python
from lexigram.search import SearchProvider
from lexigram.search.config import SearchConfig, BackendType

# Single backend — resolves as SearchEngineProtocol
app.add_provider(SearchProvider.with_meilisearch(url="http://localhost:7700"))

# Multi-backend — each is Annotated[SearchEngineProtocol, Named(name)]
provider = SearchProvider.configure(SearchConfig(backends=[...]))
app.add_provider(provider)
```

### Backend Types

| Backend | Extra | Config Section | Type |
|---------|-------|---------------|------|
| Memory | (none) | — | `BackendType.MEMORY` |
| MeiliSearch | `[meilisearch]` | `meilisearch` | `BackendType.MEILISEARCH` |
| Elasticsearch | `[elasticsearch]` | `elasticsearch` | `BackendType.ELASTICSEARCH` |
| OpenSearch | `[elasticsearch]` | `opensearch` | `BackendType.OPENSEARCH` |
| Typesense | `[typesense]` | `typesense` | `BackendType.TYPESENSE` |
| PostgreSQL FTS | `[postgres]` | `postgres` | `BackendType.POSTGRES` |
| MySQL FULLTEXT | `[mysql]` | `mysql` | `BackendType.MYSQL` |
| SQLite FTS5 | `[sqlite]` | `sqlite` | `BackendType.SQLITE` |
| MongoDB Text | `[mongodb]` | `mongo` | `BackendType.MONGODB` |

### Result Types

Search operations return domain models, not raw backend responses:

```python
from lexigram.search import SearchResponse, SearchResult, SearchQuery

# Build a query
query = SearchQuery(query="hello", page=1, per_page=20)

# The SearchEngine returns SearchResponse
response: SearchResponse = await engine.search("hello")
for result in response.results:
    print(result.score, result.data["title"])
```

### Validation

Queries and filter inputs are validated before reaching the backend:

```python
from lexigram.search import (
    validate_search_query,
    sanitize_search_query,
    SearchQueryValidator,
)
```

## Typical Usage

### Index and search with MeiliSearch

```python
from lexigram.search import SearchProvider
from lexigram.search.config import SearchConfig, BackendType, MeiliSearchConfig
from lexigram.contracts.search import SearchEngineProtocol

config = SearchConfig(
    backend_type=BackendType.MEILISEARCH,
    meilisearch=MeiliSearchConfig(
        url="http://localhost:7700",
        api_key="optional-key",
    ),
)
app.add_provider(SearchProvider.configure(config))

# Later, in a service:
engine = await container.resolve(SearchEngineProtocol)
await engine.index_document("user-42", {"name": "Alice", "email": "alice@ex.com"})
response = await engine.search("alice")
```

### Multi-backend setup

```python
from lexigram.search.config import (
    NamedSearchConfig,
    SearchConfig,
    BackendType,
    MeiliSearchConfig,
    PostgresSearchConfig,
)

config = SearchConfig(
    backends=[
        NamedSearchConfig(
            name="primary",
            primary=True,
            backend_type=BackendType.MEILISEARCH,
            meilisearch=MeiliSearchConfig(url="http://localhost:7700"),
        ),
        NamedSearchConfig(
            name="audit",
            backend_type=BackendType.POSTGRES,
            postgres=PostgresSearchConfig(connection_string="postgresql://..."),
        ),
    ]
)
provider = SearchProvider.configure(config)
app.add_provider(provider)

# Resolve by name
from lexigram.di import Named
from typing import Annotated

primary = await container.resolve(Annotated[SearchEngineProtocol, Named("primary")])
```

## Common Patterns

### Use SearchModule for encapsulation

```python
from lexigram.search import SearchModule
from lexigram.search.config import SearchConfig

app.add_module(SearchModule.configure(SearchConfig(backend_type="memory")))
```

For testing:

```python
SearchModule.stub()  # in-memory, no external deps
```

### Federated search across backends

```python
from lexigram.search import FederatedSearchEngine

federated = FederatedSearchEngine(engines=[primary, secondary])
results = await federated.search("query", merge_strategy="rank")
```

### Custom document transformation

```python
from lexigram.contracts.search import DocumentTransformerProtocol

class ArticleTransformer:
    def transform(self, entity: Article) -> dict[str, str]:
        return {"id": entity.id, "title": entity.title, "content": entity.body}

    def transform_batch(self, entities: list[Article]) -> list[dict[str, str]]:
        return [self.transform(e) for e in entities]
```

### Validation and sanitization

```python
from lexigram.search import validate_search_query, sanitize_search_filters

validate_search_query("user input")  # raises SearchValidationError on bad input
clean_filters = sanitize_search_filters(raw_filters)
```

## Best Practices

- Use `SearchProvider.with_memory()` in tests to avoid external service dependencies
- Prefer `index_many()` over individual `index_document()` calls for batch operations
- Set `fuzzy: true` on `QueryConfig` for typo-tolerant search
- Enable `SearchAnalyticsRecorder` to track search metrics per user/session
- Configure `SearchOperationsConfig.max_retries` for production resilience
- For multi-backend setups, mark one backend as `primary: true` for unnamed resolution
