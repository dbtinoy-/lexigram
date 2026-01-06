# Collision Triage Report

Generated: 2026-06-19
Total COLLISION findings: 10

Grouped by pattern category to aid allowlist review.

## OTHER (10)

### `AuditQueryService`
_Packages: lexigram-ai-governance, lexigram-audit_

- **lexigram-ai-governance** `audit/query.py:69` class
- **lexigram-audit** `query.py:16` class

### `AuditRepositoryMixin`
_Packages: lexigram-admin, lexigram-sql_

- **lexigram-admin** `core/resilience_config.py:134` class → `(Generic)`
- **lexigram-sql** `audit/mixin.py:17` class

### `Field`
_Packages: lexigram-admin, lexigram-sql_

- **lexigram-admin** `forms/fields/_base.py:390` variable = `AbstractField`
- **lexigram-sql** `schema/model.py:78` class

### `MemoryProvider`
_Packages: lexigram-ai-memory, lexigram-features, lexigram-testing_

- **lexigram-ai-memory** `di/provider.py:39` class → `(Provider)`
- **lexigram-features** `backends/testing.py:17` class → `(LocalProvider)`
- **lexigram-testing** `memory/di/provider.py:24` class → `(Provider)`

### `MetricsCollector`
_Packages: lexigram-ai-llm, lexigram-ui_

- **lexigram-ai-llm** `metrics/collector.py:193` class
- **lexigram-ui** `performance/observability.py:38` class

### `Page`
_Packages: lexigram-admin, lexigram-sql, lexigram-web_

- **lexigram-admin** `pages/base.py:18` class → `(ABC)`
- **lexigram-sql** `pagination/offset.py:18` class → `(Generic)`
- **lexigram-web** `pagination/models.py:102` class → `(Generic)`

### `SchemaDiff`
_Packages: lexigram-graphql, lexigram-sql_

- **lexigram-graphql** `schema/diff.py:13` class
- **lexigram-sql** `types.py:80` class

### `SessionManagerImpl`
_Packages: lexigram-ai-session, lexigram-auth_

- **lexigram-ai-session** `manager/core.py:37` class → `(SessionManagerProtocol)`
- **lexigram-auth** `session/manager.py:33` class

### `TransformationPipeline`
_Packages: lexigram-ai-rag, lexigram-search_

- **lexigram-ai-rag** `query/pipeline.py:6` class
- **lexigram-search** `indexing/transformer.py:29` class

### `field`
_Packages: lexigram-graphql, lexigram-sql_

- **lexigram-graphql** `schema/decorators.py:186` function
- **lexigram-sql** `repositories/filter_objects.py:198` function
