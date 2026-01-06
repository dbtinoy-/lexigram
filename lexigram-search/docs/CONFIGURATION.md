---
title: lexigram-search Configuration
description: All configuration keys for the search subsystem.
---

Config section: `search` (`SearchConfig`). Env prefix: `LEX_SEARCH__`.

## Root Options

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_SEARCH__ENABLED` | Enable the search subsystem |
| `backend_type` | `BackendType` | `memory` | `LEX_SEARCH__BACKEND_TYPE` | Search backend provider |
| `timeout` | `float` | `30.0` | `LEX_SEARCH__TIMEOUT` | Default request timeout (seconds) |
| `database` | `str \| None` | `None` | `LEX_SEARCH__DATABASE` | Named database for DB-backed backends |
| `backends` | `list[NamedSearchConfig]` | `[]` | — | Multi-backend declarations |

## Query Options (`query:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `query.strategy` | `str` | `"fuzzy"` | `LEX_SEARCH__QUERY__STRATEGY` | Search strategy |
| `query.default_limit` | `int` | `20` | `LEX_SEARCH__QUERY__DEFAULT_LIMIT` | Default results per page |
| `query.max_limit` | `int` | `100` | `LEX_SEARCH__QUERY__MAX_LIMIT` | Maximum results allowed |
| `query.enable_highlighting` | `bool` | `True` | `LEX_SEARCH__QUERY__ENABLE_HIGHLIGHTING` | Enable search term highlighting |
| `query.enable_faceting` | `bool` | `True` | `LEX_SEARCH__QUERY__ENABLE_FACETING` | Enable faceted search |
| `query.enable_aggregations` | `bool` | `False` | `LEX_SEARCH__QUERY__ENABLE_AGGREGATIONS` | Enable result aggregations |
| `query.fuzzy_threshold` | `float` | `0.8` | `LEX_SEARCH__QUERY__FUZZY_THRESHOLD` | Fuzzy matching threshold |

## Operations (`operations:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `operations.max_retries` | `int` | `3` | `LEX_SEARCH__OPERATIONS__MAX_RETRIES` | Max retry attempts |
| `operations.retry_backoff` | `float` | `0.5` | `LEX_SEARCH__OPERATIONS__RETRY_BACKOFF` | Retry backoff multiplier |
| `operations.request_timeout` | `float` | `30.0` | `LEX_SEARCH__OPERATIONS__REQUEST_TIMEOUT` | Request timeout (seconds) |
| `operations.bulk_chunk_size` | `int` | `500` | `LEX_SEARCH__OPERATIONS__BULK_CHUNK_SIZE` | Bulk request chunk size |

## MeiliSearch (`meilisearch:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `meilisearch.url` | `str` | `"http://localhost:7700"` | `LEX_SEARCH__MEILISEARCH__URL` | MeiliSearch server URL |
| `meilisearch.api_key` | `SecretStr \| None` | `None` | `LEX_SEARCH__MEILISEARCH__API_KEY` | API key |
| `meilisearch.timeout` | `int` | `30` | `LEX_SEARCH__MEILISEARCH__TIMEOUT` | Request timeout |
| `meilisearch.max_connections` | `int` | `10` | `LEX_SEARCH__MEILISEARCH__MAX_CONNECTIONS` | Max connections |
| `meilisearch.typo_tolerance_enabled` | `bool` | `True` | — | Enable typo tolerance |
| `meilisearch.searchable_attributes` | `list[str]` | `["title","name","description","content","text","body"]` | — | Fields to search |
| `meilisearch.filterable_attributes` | `list[str]` | `[]` | — | Attribute-based filtering |
| `meilisearch.sortable_attributes` | `list[str]` | `["created_at","updated_at"]` | — | Attribute-based sorting |

## Elasticsearch (`elasticsearch:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `elasticsearch.hosts` | `list[str]` | `["http://localhost:9200"]` | `LEX_SEARCH__ELASTICSEARCH__HOSTS` | Elasticsearch hosts |
| `elasticsearch.api_key` | `SecretStr \| None` | `None` | `LEX_SEARCH__ELASTICSEARCH__API_KEY` | API key |
| `elasticsearch.username` | `str \| None` | `None` | `LEX_SEARCH__ELASTICSEARCH__USERNAME` | Basic auth username |
| `elasticsearch.password` | `SecretStr \| None` | `None` | `LEX_SEARCH__ELASTICSEARCH__PASSWORD` | Basic auth password |
| `elasticsearch.use_ssl` | `bool` | `False` | `LEX_SEARCH__ELASTICSEARCH__USE_SSL` | Enable SSL |
| `elasticsearch.verify_certs` | `bool` | `True` | — | Verify SSL certificates |
| `elasticsearch.index_prefix` | `str` | `"lexigram_search_"` | — | Index name prefix |
| `elasticsearch.number_of_shards` | `int` | `1` | — | Number of shards |
| `elasticsearch.number_of_replicas` | `int` | `0` | — | Number of replicas |

## PostgreSQL (`postgres:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `postgres.connection_string` | `SecretStr` | `""` | `LEX_SEARCH__POSTGRES__CONNECTION_STRING` | Connection string |
| `postgres.text_search_config` | `str` | `"english"` | — | Text search configuration |
| `postgres.enable_trigram` | `bool` | `True` | — | Enable pg_trgm extension |
| `postgres.auto_create_tables` | `bool` | `True` | — | Auto-create search tables |

## SQLite (`sqlite:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `sqlite.db_path` | `str` | `":memory:"` | `LEX_SEARCH__SQLITE__DB_PATH` | Database file path |
| `sqlite.tokenizer` | `str` | `"porter unicode61"` | — | FTS5 tokenizer |
| `sqlite.auto_create_tables` | `bool` | `True` | — | Auto-create FTS tables |

## Typesense (`typesense:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `typesense.api_key` | `SecretStr \| None` | `None` | `LEX_SEARCH__TYPESENSE__API_KEY` | API key |
| `typesense.nodes` | `list[dict]` | `[{"host":"localhost","port":"8108","protocol":"http"}]` | — | Cluster nodes |
| `typesense.connection_timeout` | `int` | `30` | — | Connection timeout |
| `typesense.health_check_interval` | `int` | `60` | — | Health check interval |

## OpenSearch (`opensearch:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `opensearch.hosts` | `list[str]` | `["http://localhost:9200"]` | — | OpenSearch hosts |
| `opensearch.index_prefix` | `str` | `"lexigram_search_"` | — | Index name prefix |
| `opensearch.username` | `str \| None` | `None` | — | Username |
| `opensearch.password` | `str \| None` | `None` | — | Password |
| `opensearch.use_ssl` | `bool` | `False` | — | Enable SSL |
| `opensearch.verify_ssl` | `bool` | `True` | — | Verify SSL certificates |
| `opensearch.timeout` | `int` | `30` | — | Request timeout |

## MongoDB (`mongo:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `mongo.connection_string` | `SecretStr` | `""` | `LEX_SEARCH__MONGO__CONNECTION_STRING` | Connection string |
| `mongo.database_name` | `str` | `"search"` | — | Database name |
| `mongo.use_atlas_search` | `bool` | `False` | — | Use Atlas Search |

## NamedSearchConfig (for `backends[]` entries)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | `str` | — | Unique backend name (DI key) |
| `primary` | `bool` | `False` | Also register under unnamed binding |
| `backend_type` | `BackendType` | `memory` | Backend for this entry |
| `database` | `str \| None` | `None` | Named database reference |
| `meilisearch` | `MeiliSearchConfig \| None` | `None` | Per-backend config |
| `elasticsearch` | `ElasticsearchConfig \| None` | `None` | Per-backend config |
| `opensearch` | `OpenSearchConfig \| None` | `None` | Per-backend config |
| `typesense` | `TypesenseConfig \| None` | `None` | Per-backend config |
| `postgres` | `PostgresSearchConfig \| None` | `None` | Per-backend config |
| `mysql` | `MySQLSearchConfig \| None` | `None` | Per-backend config |
| `sqlite` | `SQLiteSearchConfig \| None` | `None` | Per-backend config |
| `mongo` | `MongoSearchConfig \| None` | `None` | Per-backend config |

## YAML Example

```yaml
search:
  enabled: true
  backend_type: meilisearch
  timeout: 10.0
  query:
    strategy: fuzzy
    default_limit: 20
    enable_highlighting: true
    fuzzy_threshold: 0.8
  meilisearch:
    url: http://localhost:7700
    api_key: "${MEILI_API_KEY}"
  operations:
    max_retries: 3
    bulk_chunk_size: 500
```

## Env-Only Example

```bash
export LEX_SEARCH__BACKEND_TYPE=meilisearch
export LEX_SEARCH__TIMEOUT=10.0
export LEX_SEARCH__MEILISEARCH__URL=http://localhost:7700
export LEX_SEARCH__MEILISEARCH__API_KEY=sk-...
export LEX_SEARCH__QUERY__STRATEGY=fuzzy
```
