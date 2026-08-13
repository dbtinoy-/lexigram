---
title: lexigram-tenancy Configuration
description: Every configuration key for the tenancy subsystem
---

Config section: `tenancy`  
Env prefix: `LEX_TENANCY__`  
Config model: `TenancyConfig`

## Top-level

| Key | Type | Default | Env var | Description |
|-----|------|---------|---------|-------------|
| `resolution` | `ResolutionConfig` | — | `LEX_TENANCY__RESOLUTION__*` | Resolver chain configuration |
| `lifecycle` | `LifecycleConfig` | — | `LEX_TENANCY__LIFECYCLE__*` | Lifecycle and isolation |
| `overrides` | `ConfigOverridesConfig` | — | `LEX_TENANCY__OVERRIDES__*` | Per-tenant config overrides |
| `integration` | `IntegrationConfig` | — | `LEX_TENANCY__INTEGRATION__*` | Cross-package integration toggles |

## ResolutionConfig

| Key | Type | Default | Env var | Description |
|-----|------|---------|---------|-------------|
| `resolvers` | `list[str]` | `["jwt_claim", "header", "subdomain", "path"]` | `LEX_TENANCY__RESOLUTION__RESOLVERS` | Ordered resolver names |
| `header_name` | `str` | `"x-tenant-id"` | `LEX_TENANCY__RESOLUTION__HEADER_NAME` | Header name for `HeaderTenantResolver` |
| `subdomain_pattern` | `str \| None` | `None` | `LEX_TENANCY__RESOLUTION__SUBDOMAIN_PATTERN` | Base domain for subdomain extraction |
| `path_pattern` | `str \| None` | `"/tenants/{tenant_id}/"` | `LEX_TENANCY__RESOLUTION__PATH_PATTERN` | Path pattern for `PathTenantResolver` |
| `jwt_claim_key` | `str` | `"tenant_id"` | `LEX_TENANCY__RESOLUTION__JWT_CLAIM_KEY` | JWT claim key |
| `validator_cache_ttl` | `int` | `300` | `LEX_TENANCY__RESOLUTION__VALIDATOR_CACHE_TTL` | Cache TTL for validated tenants (seconds) |

## LifecycleConfig

| Key | Type | Default | Env var | Description |
|-----|------|---------|---------|-------------|
| `isolation_strategy` | `str` | `"row_level"` | `LEX_TENANCY__LIFECYCLE__ISOLATION_STRATEGY` | Name of isolation strategy |
| `auto_provision_isolation` | `bool` | `True` | `LEX_TENANCY__LIFECYCLE__AUTO_PROVISION_ISOLATION` | Auto-provision on tenant creation |

## ConfigOverridesConfig

| Key | Type | Default | Env var | Description |
|-----|------|---------|---------|-------------|
| `cache_ttl` | `int` | `60` | `LEX_TENANCY__OVERRIDES__CACHE_TTL` | Cache TTL for per-tenant config (seconds) |

## IntegrationConfig

| Key | Type | Default | Env var | Description |
|-----|------|---------|---------|-------------|
| `cache_key_prefix` | `bool` | `True` | `LEX_TENANCY__INTEGRATION__CACHE_KEY_PREFIX` | Prefix cache keys with tenant ID |
| `sql_context_bridge` | `bool` | `True` | `LEX_TENANCY__INTEGRATION__SQL_CONTEXT_BRIDGE` | Sync tenant context into SQL sessions |

## Example YAML

```yaml
tenancy:
  resolution:
    resolvers:
      - header
      - jwt_claim
    header_name: x-tenant-id
    jwt_claim_key: tenant_id
  lifecycle:
    isolation_strategy: row_level
    auto_provision_isolation: true
  overrides:
    cache_ttl: 120
  integration:
    cache_key_prefix: true
    sql_context_bridge: true
```

Env var override form:

```bash
export LEX_TENANCY__RESOLUTION__RESOLVERS='["header"]'
export LEX_TENANCY__LIFECYCLE__ISOLATION_STRATEGY=schema
```
