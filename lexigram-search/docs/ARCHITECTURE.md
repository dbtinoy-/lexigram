# Architecture

Internal design of the `lexigram-search` package.

---

## Role in the System

`lexigram-search` provides **full-text and faceted search** as a pluggable abstraction layer. It sits between domain services and search backends (Elasticsearch, MeiliSearch, Typesense, SQL-based FTS), translating `SearchEngineProtocol` calls into backend-specific operations.

```mermaid
flowchart BT
    subgraph Application[Application Layer]
        DS[Domain Services]
    end
    subgraph Search[lexigram-search]
        SE[SearchEngine]
        QB[QueryBuilder]
        DI[DocumentIndexer]
        FT[FilterSetTranslator]
    end
    subgraph Backends[Backend Implementations]
        ES[Elasticsearch]
        MS[MeiliSearch]
        TS[Typesense]
        PG[PostgreSQL FTS]
        SL[SQLite FTS5]
        MY[MySQL FULLTEXT]
        MG[MongoDB]
        NULL[NullBackend]
    end
    subgraph Contracts[lexigram-contracts]
        SEP[SearchEngineProtocol]
        CP[CacheBackendProtocol]
    end

    DS --> SE
    SE --> QB
    SE --> DI
    FT --> SE
    SE --> SEP
    SE --> CP
    SEP --> ES
    SEP --> MS
    SEP --> TS
    SEP --> PG
    SEP --> SL
    SEP --> MY
    SEP --> MG
    SEP --> NULL
```

**Import direction rule:** Arrows point toward the dependency. Application code depends on `SearchEngineProtocol` from contracts, NOT on backend implementations. Backend implementations satisfy `SearchEngine` structurally (protocol) — no inheritance required.

---

## Backend Abstraction

The package uses a **structural protocol** pattern with two layers:

### `SearchBackend` (structural protocol in `protocols.py`)

Defines the minimal contract every search backend must satisfy:

- `index(index_name, documents)` — bulk indexing
- `search(index_name, query, filters, limit, offset)` — query execution
- `health_check(timeout)` — operational health

### `SearchEngine` (abstract base in `engine/base.py`)

Extends the protocol with index lifecycle operations (create, delete, exist check) and a richer search signature. All concrete backends satisfy this interface.

### Supported Backends

```mermaid
flowchart LR
    subgraph Dedicated[Search-Native]
        MS[MeiliSearch]
        ES[Elasticsearch]
        OS[OpenSearch]
        TS[Typesense]
        NULL[NullBackend]
    end
    subgraph SQL[SQL / Database]
        PG[PostgreSQL FTS<br/>pg_trgm]
        MY[MySQL FULLTEXT]
        SL[SQLite FTS5]
    end
    subgraph Document[Document / NoSQL]
        MG[MongoDB text search]
    end

    MS -->|Optional| MSV[MeiliSearchConfig]
    ES -->|Optional| ESV[ElasticsearchConfig]
    OS -->|Optional| OSV[OpenSearchConfig]
    TS -->|Optional| TSV[TypesenseConfig]
    PG -->|Required| PGV[PostgresSearchConfig<br/>uses DatabaseProviderProtocol]
    MY -->|Required| MYV[MySQLSearchConfig<br/>uses DatabaseProviderProtocol]
    SL -->|Required| SLV[SQLiteSearchConfig]
    MG -->|Required| MGV[MongoSearchConfig]
```

SQL-backed backends (Postgres, MySQL) are resolved lazily during `boot()` — they register a `NullBackend` placeholder during `register()` and swap in the real backend resolved from the container's `DatabaseProviderProtocol` at boot time.

```mermaid
sequenceDiagram
    participant P as SearchProvider
    participant C as Container
    participant DB as DatabaseProviderProtocol
    participant BE as Real Backend

    P->>P: configure() — detects POSTGRES/MYSQL
    P->>P: Sets _uses_db_backend=True
    P->>C: register() — NullBackend placeholder
    C->>P: boot()
    P->>C: resolve(DatabaseProviderProtocol)
    C->>DB: Provide database connection
    DB-->>P: Database provider
    P->>P: Instantiate Postgres/MysqlSearchBackend
    P->>P: Replace NullBackend → Real Backend
    P->>BE: health_check()
    BE-->>P: Healthy
```

---

## Indexing Pipeline

Documents flow through a transformation pipeline before reaching the search backend:

```mermaid
sequenceDiagram
    actor App as Application Code
    participant TE as SearchEngine
    participant DTF as DocumentTransformer
    participant BI as BatchIndexer
    participant BE as Backend

    App->>TE: index_many(index, documents)
    TE->>DTF: to_target_batch(sources)
    DTF->>DTF: Pipeline 1: pre_transform
    DTF->>DTF: Pipeline N: transformation rules
    DTF->>DTF: Pipeline N: post_transform
    DTF-->>TE: Transformed documents
    TE->>BI: index_documents(index, documents)
    BI->>BI: Slice into batches (configurable size)
    BI->>BE: bulk_operation(batch 1)
    BI->>BE: bulk_operation(batch 2)
    BI->>BE: bulk_operation(batch N)
    BE-->>BI: BulkResult
    BI-->>TE: BatchStats
    TE-->>App: BatchStats
```

The `DocumentTransformer` extends `ReadOnlyMapper[dict, dict]` from `lexigram.data.mapper`. Transformation pipelines consist of ordered `TransformationRule` instances, each with an optional condition and error handling:

| Component | Role |
|-----------|------|
| `TransformationRule` | A single field transform with optional condition |
| `TransformationPipeline` | Named sequence of rules, pre/post hooks |
| `DocumentTransformer` | Applies pipelines via `to_target()` / `to_target_batch()` |
| `FieldMapper` | Renames document fields before indexing |
| `ValueTransformer` | Transforms individual field values |

---

## Search Query Model

Search queries are built through a **fluent builder** that composes filters, facets, pagination, sorting, and advanced query types:

```mermaid
flowchart LR
    subgraph Builder[SearchQueryBuilder]
        Q(query) --> B[build]
        W(where) --> B
        WI(where_in) --> B
        WB(where_between) --> B
        O(order_by) --> B
        S(select) --> B
        F(facet) --> B
        A(aggregate) --> B
        H(highlight) --> B
        FU(fuzzy) --> B
        AU(autocomplete) --> B
        GD(geo_distance) --> B
        P(page) --> B
        FE(filter_expr) --> B
    end
    B --> SQ[SearchQuery]
    SQ -->|Backend-native translation| Qt[QueryTranslator - TranslatedQuery]
    Qt --> ES[Elasticsearch DSL]
    Qt --> PG[PostgreSQL SQL]
    Qt --> MS[MeiliSearch API]

    subgraph Types[Query Types]
        FC[FilterCondition]
        SF[SortField]
        ASP[AggregationSpec]
        FZ[FuzzyQuery]
        AC[AutocompleteQuery]
        GD2[GeoDistanceFilter]
    end
```

The builder exposes a chained API:

```python
query = (
    SearchQueryBuilder()
    .query("python")
    .where("status", "active")
    .where_between("score", 80, 100)
    .facet("category")
    .order_by_desc("score")
    .highlight(fields=["title", "description"])
    .page(1, 20)
    .build()
)
result = await engine.search("documents", query)
```

### Filter Expression Support

Beyond simple flat conditions, the builder accepts composable `FilterExpression` trees (`AndExpression`, `OrExpression`, `NotExpression`) from `lexigram.contracts.data` via `filter_expr()`.

### Admin-Facing FilterSet

The `FilterSetTranslator` converts an admin-facing `FilterSet` (with `FilterOperator` enum) into a `SearchQuery`:

```python
fs = FilterSet(
    conditions=(
        FilterCondition("status", FilterOperator.EQ, "active"),
        FilterCondition("score", FilterOperator.GTE, 80),
    ),
    order_by="name",
    page=1, page_size=10,
    search_query="python",
)
search_query = FilterSetTranslator().translate(fs)
```

---

## Provider Lifecycle

`SearchProvider` is registered at `ProviderPriority.DOMAIN` — after infrastructure (database, cache) but before presentation (web).

```mermaid
sequenceDiagram
    actor App as Application
    participant SP as SearchProvider
    participant C as Container
    participant BE as Backend
    participant Cache as CacheBackendProtocol

    Note over SP: register() — ContainerRegistrarProtocol
    App->>SP: SearchProvider.configure(config)
    SP->>SP: Create backend instance (or NullBackend placeholder)
    App->>SP: register(container)
    alt multi-backend mode
        SP->>C: Named[SearchEngine, "primary"]
        SP->>C: Named[SearchEngine, "audit"]
        SP->>C: SearchEngine (unnamed = primary)
    else single-backend mode
        SP->>C: SearchEngine (singleton)
    end
    SP->>C: SearchProvider (singleton)

    Note over SP: boot() — ContainerResolverProtocol
    App->>SP: boot(container)
    alt DB-backed backend pending
        SP->>C: resolve(DatabaseProviderProtocol)
        C-->>SP: DatabaseProvider
        SP->>SP: Replace NullBackend → real backend
    end
    SP->>BE: health_check()
    BE-->>SP: Healthy

    Note over SP: Runtime — search queries
    App->>C: resolve(SearchEngine)
    C-->>App: Backend instance
    App->>BE: search("products", "laptop")
    alt cache enabled
        BE->>Cache: get(cache_key) / set(cache_key, ttl=300)
    end

    Note over SP: shutdown()
    App->>SP: shutdown()
    SP->>BE: close()
```

### Provider Priorities

`SearchProvider` uses `ProviderPriority.DOMAIN` — it boots after infrastructure (database, cache) but before presentation (web).

### Multi-Backend Mode

When `SearchConfig.backends` is non-empty, the provider registers each entry as `Annotated[SearchEngineProtocol, Named(entry.name)]`. The primary backend receives both the named binding and the unnamed default binding for backward compatibility.

```python
config = SearchConfig(backends=[
    NamedSearchConfig(name="primary", primary=True, backend_type="meilisearch"),
    NamedSearchConfig(name="audit", backend_type="postgres", database="audit_db"),
])
```

---

## Contracts Used

| Protocol | Location in Contracts | Implemented By |
|----------|----------------------|---------------|
| `SearchEngineProtocol` | `lexigram.contracts.search` | `SearchEngine` ABC, `DefaultSearchEngine`, `FederatedSearchEngine`, each backend, `CachedSearchBackend` |
| `SearchableProtocol` | `lexigram.contracts.search` | `SearchableModel` |
| `IndexManagerProtocol` | `lexigram.contracts.search` | Per-backend index managers |
| `SearchAnalyticsProtocol` | `lexigram.contracts.search` | `SearchAnalyticsRecorder` |
| `DocumentTransformerProtocol` | `lexigram.contracts.search` | `DocumentTransformer`, `DefaultDocumentTransformer` |
| `DatabaseSearchBackendProtocol` | `lexigram.contracts.search` | Postgres/MySQL backends |
| `CacheBackendProtocol` | `lexigram.contracts.infra.cache` | `CachedSearchBackend` (wraps an inner backend) |
| `DatabaseProviderProtocol` | `lexigram.contracts.data` | Resolved at boot for SQL-backed backends |
| `FilterExpression` | `lexigram.contracts.data` | `SearchQueryBuilder.filter_expr()` |
| `HookRegistryProtocol` | `lexigram.contracts.hooks` | `SearchIndexedHook`, `SearchQueryExecutedHook` |
| `EventBusProtocol` | `lexigram.contracts.events` | `IndexingCompletedEvent`, `SearchExecutedEvent` |

---

## Exception Convention

```mermaid
flowchart LR
    subgraph Contracts[lexigram-contracts]
        LE[LexigramError]
        DE[DomainError]
        IE[InfrastructureError]
    end
    subgraph Search[lexigram-search]
        SE[SearchError]
        INFE[IndexNotFoundError<br/>DomainError]
        BE[BackendError<br/>InfrastructureError]
        SVE[SearchValidationError]
        QE[QueryError]
        TE[TransformationError]
        CE[CacheError]
        SIE[SearchIndexError]
        SCHE[SchedulerError]
        CFGE[ConfigurationError]
    end

    LE --> DE
    LE --> IE
    SE -->|extends| LE
    INFE --> DE
    BE --> IE
    SVE --> SE
    QE --> SE
    TE --> SE
    CE --> SE
    SIE --> SE
    SCHE --> SE
    CFGE --> SE
```

Domain search errors use the `Result[T, E]` pattern — every `search()`, `index()`, and `create_index()` call returns `Result[..., SearchError]`. Infrastructure failures (connection lost, timeout) propagate as exceptions from `BackendError`.

---

## Cached Backend

`CachedSearchBackend` decorates any `SearchEngine` with a cache-aside pattern:

```python
from lexigram.search.backends.cached import CachedSearchBackend

backend = CachedSearchBackend(
    inner=NullBackend(),
    cache=cache_backend,  # resolved from container
    ttl=300,
)
```

- **Read path**: Cache key is a deterministic hash of `(index, query, filters, limit, offset, sort)`. Cache hit returns `Ok(response)` without touching the backend.
- **Write path**: Index/update/delete operations pass through and invalidate the affected index's cache entries.
- **Failure isolation**: Cache unavailability (connection error, timeout) logs a warning and falls through to the inner backend — never fails the search.

---

## Query Translation

Each backend with non-trivial query syntax (Elasticsearch, PostgreSQL) implements a `QueryTranslator` subclass that converts the unified `SearchQuery` into backend-native format:

| Translator | Output Format |
|------------|---------------|
| `PostgresQueryTranslator` | Raw SQL with `websearch_to_tsquery` parameters |
| `ElasticsearchQueryTranslator` | Elasticsearch Query DSL dict |
| (MeiliSearch, Typesense, SQLite) | Direct API calls via their SDK |

The `TranslatedQuery` dataclass carries the translated query, params, options, aggregations, and highlight definitions.

---

## Search Suggestions

`SuggestionEngine` provides query suggestion/autocomplete capabilities:

```python
from lexigram.search.query import SuggestionEngine

engine = SuggestionEngine(search_backend=backend)
suggestions = await engine.suggest("pyth")
# → ["python", "python django", "python async"]
```

Supports per-query result limiting, and can be backed by any registered search backend.

---

## Federation

`FederatedSearchEngine` wraps a `SearchEngineProtocol` and searches across multiple indices simultaneously, combining results:

```python
federated = FederatedSearchEngine(engine=search_engine, indices=["products", "documents"])
results = await federated.search_across("laptop", limit_per_index=10)
```

Supports per-index limits, total result caps, index-specific filtering, and **fallback search** — if primary indices return insufficient results, secondary indices are queried automatically.

---

## Reindexing

`ReindexManager` performs zero-downtime index rebuilds:

1. Creates a **shadow index** (`{name}_reindex_{timestamp}`)
2. Streams documents from an `AsyncIterator` in batches
3. **Swaps** atomically using aliases (Elasticsearch) or drop-and-rename (other backends)

```python
manager = ReindexManager(engine=search_engine, batch_size=500)

async def my_source():
    async for item in db.stream_all():
        yield item.to_dict()

await manager.reindex("users", source=my_source())
```

---

## Indexing Scheduler

`IndexingScheduler` runs periodic indexing jobs:

- Configurable interval, batch size, concurrency, and retry
- `asyncio`-based scheduler loop with semaphore-limited concurrency
- Tracks per-job stats (processed, failed, throughput)
- Supports immediate execution via `run_job_now()`

---

## Source Layout

```
src/lexigram/search/
├── __init__.py              # Lazy public API exports
├── config.py                # SearchConfig, BackendType, per-backend configs
├── constants.py             # Default values, backend name strings
├── exceptions.py            # SearchError, BackendError, QueryError, …
├── types.py                 # SearchResult, SearchResponse, SearchQuery, SearchStrategy
├── protocols.py             # SearchBackend, Indexer, QueryBuilder (structural)
├── module.py                # SearchModule — DynamicModule wrapper
├── di/
│   └── provider.py          # SearchProvider — register, boot, shutdown
├── engine/
│   ├── base.py              # SearchEngine protocol (structural)
│   ├── engine.py            # DefaultSearchEngine, BulkOperationResult, BulkResult
│   ├── federation.py        # FederatedSearchEngine, FederatedResults
│   ├── models.py            # SearchableModel
│   └── validation.py        # Query length, structure validation
├── backends/
│   ├── base/backend.py      # SearchBackendBase (ABC + AbstractReadOnlyRepository)
│   ├── factory.py           # Backend factory (get_backend)
│   ├── cached.py            # CachedSearchBackend (decorator)
│   ├── translate.py         # QueryTranslator ABC, PostgresQueryTranslator, ES translator
│   ├── null.py              # NullBackend (in-memory noop)
│   ├── meilisearch/         # MeiliSearchBackend
│   ├── elasticsearch/       # Elasticsearch / OpenSearch backends
│   ├── typesense/           # Typesense backend
│   ├── sqlite/              # SQLite FTS5 backend
│   ├── postgres/            # PostgreSQL FTS backend (resolved via DatabaseProviderProtocol)
│   ├── mysql/               # MySQL FULLTEXT backend
│   └── mongodb/             # MongoDB text search backend
├── query/
│   ├── builder.py           # SearchQueryBuilder (fluent API)
│   ├── types.py             # FilterCondition, SortField, AggregationSpec, FuzzyQuery, …
│   ├── operator_registry.py # Query operator registry
│   ├── filters.py           # Filter utilities
│   ├── safe_query.py        # SafeSearchQuery validation
│   ├── suggestions.py       # SuggestionEngine
│   └── validation.py        # Query validation
├── filterset/
│   ├── types.py             # FilterCondition, FilterOperator, FilterSet
│   └── translator.py        # FilterSetTranslator
├── indexing/
│   ├── transformer.py       # DocumentTransformer, TransformationPipeline, FieldMapper
│   ├── batch.py             # BatchIndexer, BatchConfig, BatchStats
│   ├── reindex.py           # ReindexManager
│   └── scheduler.py         # IndexingScheduler, IndexingJob, ScheduleConfig
├── analytics/
│   └── recorder.py          # SearchAnalyticsRecorder, InMemorySearchAnalyticsRecorder
├── repository/
│   └── entity_repository.py # SearchEntityRepository
├── validation/
│   ├── validator.py         # SearchQueryValidator
│   └── functions.py         # sanitize_search_query, validate_index_name, …
├── hooks.py                 # SearchIndexedHook, SearchQueryExecutedHook
└── events.py                # IndexingCompletedEvent, SearchExecutedEvent
```

---

## Extension Points

| Point | Mechanism |
|-------|-----------|
| Custom backend | Implement `SearchBackend` protocol (structural) — no subclass required |
| Custom document transformer | Subclass `DocumentTransformer`, override `to_target()` |
| Custom query builder | Implement `QueryBuilder` protocol, register via `SearchProvider` |
| Custom query translator | Subclass `QueryTranslator`, implement `translate_search()` |
| Custom analytics | Implement `SearchAnalyticsProtocol`, pass to `SearchAnalyticsRecorder` |
| Custom filter set translator | Subclass `FilterSetTranslator` for backend-specific filter syntax |
| Index lifecycle hooks | Subscribe to `SearchIndexedHook` / `SearchQueryExecutedHook` |
| Domain events | Subscribe to `IndexingCompletedEvent` / `SearchExecutedEvent` via `EventBusProtocol` |
| Search result caching | Wrap any backend with `CachedSearchBackend` + `CacheBackendProtocol` |
| Periodic indexing | Add a `IndexingJob` to `IndexingScheduler` with a data source callable |
