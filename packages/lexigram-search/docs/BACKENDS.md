---
title: lexigram-search Backends
description: Supported search backends in lexigram-search — MeiliSearch, Elasticsearch, OpenSearch, Typesense, SQL-native, and in-memory
---

`lexigram-search` supports multiple full-text search backends through a common `SearchEngine` protocol. Each backend implements indexing, querying, filtering, faceting, and health-checking against the same interface, so you can switch between them with a config change.

## Supported Backends

| Backend | Extra / Package | Production Ready | Best For |
|---------|----------------|-----------------|----------|
| **MeiliSearch** | `[meilisearch]` | Yes | Typo-tolerant search, e-commerce, instant search |
| **Elasticsearch** | `[elasticsearch]` | Yes | Large-scale analytics, complex aggregations |
| **OpenSearch** | `[elasticsearch]` | Yes | AWS-compatible Elasticsearch, open-source search |
| **Typesense** | `[algolia]` | Yes | Low-latency typo-tolerant search, Algolia alternative |
| **PostgreSQL FTS** | `[postgres]` | Yes | Direct SQL full-text, no extra infra |
| **MySQL FULLTEXT** | `[mysql]` | Yes | MySQL-native full-text, no extra infra |
| **SQLite FTS5** | `[sqlite]` | Dev/Test | Embedded search, CI, local dev |
| **MongoDB Text** | `[mongodb]` | Yes | Atlas Search, MongoDB-native text search |
| **Memory (null)** | *(none)* | No | Unit tests, prototyping |

### MeiliSearch

Typo-tolerant search with instant response times. MeiliSearch provides out-of-the-box ranking rules (words, typo, proximity, attribute, sort, exactness), faceted search, and synonym management. Best for customer-facing search where usability matters more than raw query syntax.

```yaml
search:
  backend_type: meilisearch
  meilisearch:
    url: http://localhost:7700
    api_key: "${MEILI_MASTER_KEY}"
```

```python
from lexigram.search import SearchProvider, SearchConfig

config = SearchConfig(backend_type="meilisearch")
config.meilisearch.url = "http://localhost:7700"
provider = SearchProvider.with_meilisearch(url="http://localhost:7700")
```

### Elasticsearch

The de-facto standard for search infrastructure. Elasticsearch supports complex aggregations, custom analyzers, multi-language stemming, and near-real-time indexing. Best when you need nested queries, geo-search, or large-scale log-style search. Configure shard count and replica count for throughput tuning.

```yaml
search:
  backend_type: elasticsearch
  elasticsearch:
    hosts: ["http://localhost:9200"]
    index_prefix: myapp_search_
    number_of_shards: 3
    number_of_replicas: 1
```

### OpenSearch

A fork of Elasticsearch favoured in AWS environments. The config model mirrors Elasticsearch with an additional `timeout` field. Use this backend when deploying on Amazon OpenSearch Service or when you need an ALv2-licensed Elasticsearch alternative.

```yaml
search:
  backend_type: opensearch
  opensearch:
    hosts: ["http://localhost:9200"]
    username: "${OPENSEARCH_USER}"
    password: "${OPENSEARCH_PASS}"
    use_ssl: true
    timeout: 30
```

### Typesense

An open-source alternative to Algolia focused on low-latency typo-tolerant search. Typesense uses a node-based cluster configuration with built-in health checking. Best for search-as-you-type experiences with minimal operational overhead.

```yaml
search:
  backend_type: typesense
  typesense:
    nodes:
      - host: localhost
        port: "8108"
        protocol: http
    api_key: "${TYPESENSE_API_KEY}"
```

### SQL-Native Backends (PostgreSQL, MySQL, SQLite)

These backends use your existing relational database for full-text search, eliminating the need for a separate search cluster. PostgreSQL uses `pg_trgm` for fuzzy matching and `tsvector` for ranking. MySQL uses `FULLTEXT` indexes. SQLite uses FTS5 virtual tables.

```yaml
search:
  backend_type: postgres
  postgres:
    connection_string: "${DATABASE_URL}"
    text_search_config: english
    enable_trigram: true
```

:::caution
SQL-native backends delegate the search workload to your OLTP database. For high-throughput search traffic, use a dedicated search backend like MeiliSearch or Elasticsearch.
:::

### MongoDB Text Search

Uses MongoDB text indexes or Atlas Search. Configured with a connection string, database name, and an optional flag to enable Atlas Search for more advanced NLP-powered queries.

```yaml
search:
  backend_type: mongodb
  mongo:
    connection_string: "${MONGO_URI}"
    database_name: search
    use_atlas_search: false
```

### Memory / Null Backend

An in-memory backend that stores documents in a dict. All data is lost on process restart. Use for unit tests and local prototyping.

```python
from lexigram.search import SearchProvider

provider = SearchProvider.with_memory()
```

## Federated Search

When you need to query multiple backends in one request, use `FederatedSearchEngine`. Configured via the `backends` list in `SearchConfig`, each backend receives a `Named()` DI binding and can be targeted individually or merged through a federated coordinator.

```yaml
search:
  backends:
    - name: products
      primary: true
      backend_type: meilisearch
      meilisearch:
        url: http://localhost:7700
    - name: docs
      backend_type: elasticsearch
      elasticsearch:
        hosts: ["http://localhost:9200"]
```

```python
from lexigram.search import SearchProvider, SearchConfig
from typing import Annotated
from lexigram.di.markers import Named

# Primary backend resolves as SearchEngine; named ones by Annotated
products: Annotated[SearchEngine, Named("products")]
docs: Annotated[SearchEngine, Named("docs")]
```

## Result Ranking

Ranking behaviour is backend-specific. MeiliSearch uses configurable ranking rules (`words`, `typo`, `proximity`, `attribute`, `sort`, `exactness`). Elasticsearch/OpenSearch use BM25 similarity with custom boosting via `function_score`. PostgreSQL uses `ts_rank` with optional trigram similarity boosts. Typesense uses a built-in scoring formula tuned for typo tolerance.

## Quick Selection Guide

| If you need… | Choose… |
|-------------|---------|
| Fast typo-tolerant search, minimal ops | MeiliSearch |
| Complex aggregations, large-scale analytics | Elasticsearch / OpenSearch |
| Low-latency search, Algolia alternative | Typesense |
| No extra infrastructure | PostgreSQL FTS or MySQL FULLTEXT |
| Embedded / CI testing | SQLite FTS5 |
| Unit tests only | Memory (null) |

## Multi-Backend Configuration

```yaml
search:
  backends:
    - name: primary
      primary: true
      backend_type: meilisearch
      meilisearch:
        url: http://localhost:7700
    - name: audit_log
      backend_type: postgres
      database: audit
      postgres:
        connection_string: "${DATABASE_URL}"
```

## Testing with Memory Backend

```python
from lexigram.search import SearchProvider


# Arrange
provider = SearchProvider.with_memory()

# Act — provider registers an in-memory NullBackend
# All search operations work identically to production
```
