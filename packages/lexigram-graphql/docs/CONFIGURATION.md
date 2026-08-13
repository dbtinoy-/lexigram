---
title: lexigram-graphql Configuration
description: Every configuration key for the GraphQL subsystem
---

Config section: `graphql`  
Env prefix: `LEX_GRAPHQL__`  
Config model: `GraphQLConfig`

## Top-level

| Key | Type | Default | Env var | Description |
|-----|------|---------|---------|-------------|
| `name` | `str` | `"graphql"` | `LEX_GRAPHQL__NAME` | Configuration name |
| `enabled` | `bool` | `True` | `LEX_GRAPHQL__ENABLED` | Enable GraphQL module |
| `path` | `str` | `"/graphql"` | `LEX_GRAPHQL__PATH` | GraphQL endpoint path |
| `debug` | `bool` | `False` | `LEX_GRAPHQL__DEBUG` | Enable debug mode; propagates to errors |
| `env` | `str \| None` | `None` | `LEX_GRAPHQL__ENV` / `LEX_ENV` | Environment name |
| `enable_identity_resolution` | `bool` | `False` | `LEX_GRAPHQL__ENABLE_IDENTITY_RESOLUTION` | Resolve OAuth IDs to internal UUIDs |
| `schema_baseline_path` | `str \| None` | `None` | `LEX_GRAPHQL__SCHEMA_BASELINE_PATH` | SDL file path for schema diffing |

## Sub-configurations

| Section | Config class | Keys |
|---------|-------------|------|
| `cache` | `CacheConfig` | `enabled`, `default_max_age`, `default_scope`, `vary_headers` |
| `depth_limit` | `DepthLimitConfig` | `enabled`, `max_depth` (default: 10), `ignore_introspection` |
| `complexity` | `ComplexityConfig` | `enabled`, `max_complexity` (default: 1000), `default_field_cost`, `default_list_cost` |
| `persisted_queries` | `PersistedQueryConfig` | `enabled`, `store_type` ("memory"/"redis"), `ttl_seconds` |
| `batch` | `BatchConfig` | `enabled`, `max_batch_size` |
| `introspection` | `IntrospectionConfig` | `enabled`, `allowed_environments` |
| `playground` | `PlaygroundConfig` | `enabled`, `path`, `title` |
| `subscriptions` | `SubscriptionConfig` | `enabled`, `path`, `protocol`, `keepalive_interval`, `connection_timeout` |
| `dataloader` | `DataLoaderConfig` | `enabled`, `batch_enabled`, `cache_enabled`, `max_batch_size`, `batch_delay_ms` |
| `tracing` | `TracingConfig` | `enabled`, `service_name`, `trace_resolvers`, `trace_dataloaders`, `sample_rate` |
| `metrics` | `MetricsConfig` | `enabled`, `namespace`, `include_labels`, `histogram_buckets` |
| `errors` | `ErrorConfig` | `mask_errors`, `include_stacktrace`, `debug_mode`, `log_errors` |
| `rate_limit` | `RateLimitConfig` | `requests_per_minute`, `enabled` |

## Example YAML

```yaml
graphql:
  path: /graphql
  debug: false
  introspection:
    enabled: true
    allowed_environments:
      - development
      - testing
  depth_limit:
    enabled: true
    max_depth: 10
  complexity:
    enabled: true
    max_complexity: 1000
  subscriptions:
    enabled: true
    protocol: graphql-transport-ws
    keepalive_interval: 30
  errors:
    mask_errors: true
    include_stacktrace: false
  rate_limit:
    requests_per_minute: 60
    enabled: true
```

## Environment configurations

```python
# Development — debugging enabled, playground on
config = GraphQLConfig.development()

# Production — security hardened
config = GraphQLConfig.production()
```
