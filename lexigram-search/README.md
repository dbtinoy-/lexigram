# lexigram-search

Full-text search and indexing for Lexigram Framework — Elasticsearch, Meilisearch, and Algolia

---

## Overview

lexigram-search provides a unified `SearchEngineProtocol` interface over Meilisearch, Elasticsearch, Typesense, PostgreSQL full-text, MySQL, MongoDB, and SQLite. It supports typo-tolerant search, faceting, fuzzy matching, result caching, and analytics. All services are wired via `SearchProvider`, which registers the search engine protocol with the DI container.

---


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-search
# Optional extras
uv add "lexigram-search[meilisearch]"     # Meilisearch
uv add "lexigram-search[elasticsearch]"   # Elasticsearch 8.x
uv add "lexigram-search[typesense]"       # Typesense
uv add "lexigram-search[postgres,mysql,sqlite,mongodb]"  # Database backends
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

# Import the module from the package
from lexigram.search import SearchModule

@module(imports=[SearchModule.configure(...)])
class AppModule(Module):
    pass

app = Application(modules=[AppModule])
if __name__ == "__main__":
    app.run()
```

## Configuration

> **Zero-config usage:** Call `SearchModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
search:
  backend_type: meilisearch
  meilisearch:
    url: http://localhost:7700
    api_key: "${MEILI_API_KEY}"
  query:
    strategy: fuzzy
    default_limit: 10
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_SEARCH__ENABLED=true
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.search.config import SearchConfig, BackendType
from lexigram.search import SearchModule

config = SearchConfig(backend_type=BackendType.MEILISEARCH, ...)
SearchModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `backend_type` | `memory` | `LEX_SEARCH__BACKEND_TYPE` | Active backend (`meilisearch`, `elasticsearch`, `typesense`, `postgres`, `mysql`, `sqlite`, `memory`) |
| `timeout` | `30.0` | `LEX_SEARCH__TIMEOUT` | Default request timeout in seconds |
| `query.strategy` | `fuzzy` | `LEX_SEARCH__QUERY__STRATEGY` | Query strategy (`fuzzy`, `exact`, `semantic`, `hybrid`) |
| `query.default_limit` | `10` | `LEX_SEARCH__QUERY__DEFAULT_LIMIT` | Default number of results returned |
| `query.max_limit` | `100` | `LEX_SEARCH__QUERY__MAX_LIMIT` | Maximum allowed result limit |
| `query.fuzzy_threshold` | `0.8` | `LEX_SEARCH__QUERY__FUZZY_THRESHOLD` | Fuzzy match threshold (0–1; 1 = exact) |
| `meilisearch.url` | `http://localhost:7700` | `LEX_SEARCH__MEILISEARCH__URL` | MeiliSearch server URL |
| `meilisearch.api_key` | `null` | `LEX_SEARCH__MEILISEARCH__API_KEY` | MeiliSearch authentication key |
| `elasticsearch.hosts` | `[http://localhost:9200]` | `LEX_SEARCH__ELASTICSEARCH__HOSTS` | Elasticsearch cluster hosts |
| `operations.bulk_chunk_size` | `500` | `LEX_SEARCH__OPERATIONS__BULK_CHUNK_SIZE` | Documents per bulk index request |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `SearchModule.configure(config, enable_facets)` | Configure with explicit SearchConfig |
| `SearchModule.stub()` | Minimal config for testing |

## Key Features

- **Protocol abstraction** — Swap backends without changing application code
- **Meilisearch** — Typo-tolerant, instant search with faceting
- **Elasticsearch** — Full Lucene query DSL; aggregations; multi-index
- **Typesense** — Fast, schema-enforced search with scoped API keys
- **PostgreSQL FTS** — `tsvector`/`tsquery` via `lexigram-sql`; no extra infra
- **MySQL FTS** — `FULLTEXT` index support for MySQL / MariaDB
- **MongoDB Text** — Native `$text` operator with language stemming
- **SQLite FTS5** — Local development with zero dependencies
- **Cached search** — Transparent result caching via `CacheBackend`
- **Analytics** — Query recording and hit-rate analytics for ranking improvement

## Testing

```python
async with Application.boot(modules=[SearchModule.stub()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/search/module.py` | `SearchModule` class with factory methods |
| `src/lexigram/search/di/provider.py` | `SearchProvider` — wires search protocols into DI container |
| `src/lexigram/search/config.py` | `SearchConfig` and sub-config classes |
| `src/lexigram/search/engine/` | Search engine implementations for each backend |
| `src/lexigram/search/indexer/` | Index management and document indexing |