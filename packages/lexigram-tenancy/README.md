# lexigram-tenancy

Multi-tenant resolution, lifecycle, and isolation for the Lexigram Framework.

---

## Overview

`lexigram-tenancy` provides a composable resolver chain (JWT claim, header, subdomain, path) for tenant identification, ASGI enforcement middleware, three data-isolation strategies (row-level, schema, database), tenant lifecycle CRUD with domain event emission, and per-tenant config overrides — all wired through Lexigram's DI/IoC container.

---


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram lexigram-tenancy

# With SQL tenant store
uv add "lexigram-tenancy[sql]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.tenancy import TenancyModule
from lexigram.tenancy.config import ResolutionConfig, TenancyConfig
from lexigram.contracts.tenancy.protocols import TenantProviderProtocol


@module(
    imports=[
        TenancyModule.configure(
            TenancyConfig(
                resolution=ResolutionConfig(
                    resolvers=["jwt_claim", "header"],
                    header_name="x-tenant-id",
                    jwt_claim_key="tenant_id",
                    validator_cache_ttl=300,
                ),
            )
        )
    ]
)
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        provider = await app.container.resolve(TenantProviderProtocol)
        tenants = await provider.list_tenants()
        print(f"Active tenants: {len(tenants)}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `TenancyModule.configure()` with no arguments to use all defaults.

### Option 1 — YAML file

```yaml
# application.yaml
tenancy:
  resolution:
    resolvers: ["jwt_claim", "header"]
    header_name: "x-tenant-id"
    jwt_claim_key: "tenant_id"
  lifecycle:
    isolation_strategy: "row_level"
    auto_provision_isolation: true
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_TENANCY__ENABLED=true
export LEX_TENANCY__RESOLUTION__RESOLVERS=["jwt_claim", "header"]
```

### Option 3 — Python

```python
from lexigram.tenancy import TenancyModule
from lexigram.tenancy.config import TenancyConfig, ResolutionConfig, LifecycleConfig

TenancyModule.configure(
    TenancyConfig(
        resolution=ResolutionConfig(
            resolvers=["jwt_claim", "header"],
            header_name="x-tenant-id",
            jwt_claim_key="tenant_id",
        ),
        lifecycle=LifecycleConfig(isolation_strategy="schema"),
    )
)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `resolution.resolvers` | `["jwt_claim", "header", "subdomain", "path"]` | `LEX_TENANCY__RESOLUTION__RESOLVERS` | Ordered resolver list; first match wins |
| `resolution.header_name` | `"x-tenant-id"` | `LEX_TENANCY__RESOLUTION__HEADER_NAME` | HTTP header read by `HeaderTenantResolver` |
| `resolution.subdomain_pattern` | `null` | `LEX_TENANCY__RESOLUTION__SUBDOMAIN_PATTERN` | Base domain for subdomain extraction |
| `resolution.jwt_claim_key` | `"tenant_id"` | `LEX_TENANCY__RESOLUTION__JWT_CLAIM_KEY` | JWT payload claim key |
| `resolution.validator_cache_ttl` | `300` | `LEX_TENANCY__RESOLUTION__VALIDATOR_CACHE_TTL` | Seconds a validated `TenantInfo` is cached |
| `lifecycle.isolation_strategy` | `"row_level"` | `LEX_TENANCY__LIFECYCLE__ISOLATION_STRATEGY` | `"row_level"`, `"schema"`, or `"database"` |
| `lifecycle.auto_provision_isolation` | `true` | `LEX_TENANCY__LIFECYCLE__AUTO_PROVISION_ISOLATION` | Run isolation strategy on tenant creation |
| `overrides.cache_ttl` | `60` | `LEX_TENANCY__OVERRIDES__CACHE_TTL` | Seconds a tenant's config dict is cached |
| `integration.cache_key_prefix` | `true` | `LEX_TENANCY__INTEGRATION__CACHE_KEY_PREFIX` | Prefix cache keys with `t:{tenant_id}:` |
| `integration.sql_context_bridge` | `true` | `LEX_TENANCY__INTEGRATION__SQL_CONTEXT_BRIDGE` | Propagate `TENANT_ID` to lexigram-sql context |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `TenancyModule.configure(config)` | Configure with explicit `TenancyConfig` |
| `TenancyModule.stub()` | Minimal config for testing (exports `TenantProviderProtocol` and `TenantConfigProviderProtocol`) |

## Key Features

- **Resolver chain** — JWT claim, header, subdomain, and path resolvers in priority order
- **ASGI middleware** — `TenantContextMiddleware` resolves tenant on every HTTP/WebSocket request
- **Three isolation strategies** — row-level (default), schema-per-tenant, database-per-tenant
- **Tenant lifecycle CRUD** — create, activate, deactivate, suspend with domain event emission
- **Per-tenant config overrides** — key-value overrides with defaults and `TenantConfigChanged` events
- **Cache key prefixing** — wraps `CacheBackendProtocol` with tenant-prefixed keys automatically
- **lexigram-sql integration** — `TenantSQLContextBridge` enables `TenantScope` and `multi_tenant=True` filtering

## Testing

```python
import pytest
from lexigram import Application
from lexigram.tenancy import TenancyModule
from lexigram.contracts.tenancy.commands import CreateTenantCommand
from lexigram.tenancy.lifecycle.service import TenantLifecycleService


@pytest.mark.asyncio
async def test_tenant_lifecycle() -> None:
    async with Application.boot(modules=[TenancyModule.stub()]) as app:
        lifecycle = await app.container.resolve(TenantLifecycleService)

        result = await lifecycle.create_tenant(
            CreateTenantCommand(slug="acme", name="ACME Corp")
        )
        assert result.is_ok()
        assert result.unwrap().slug == "acme"
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/tenancy/module.py` | `TenancyModule.configure()`, `.stub()` |
| `src/lexigram/tenancy/config.py` | `TenancyConfig`, `ResolutionConfig`, `LifecycleConfig` |
| `src/lexigram/tenancy/di/provider.py` | `TenancyProvider` bundle and sub-providers |
| `src/lexigram/tenancy/resolution/chain.py` | `CompositeResolver` |
| `src/lexigram/tenancy/enforcement/middleware.py` | `TenantContextMiddleware` |
| `src/lexigram/tenancy/enforcement/guard.py` | `TenantGuard` |
| `src/lexigram/tenancy/lifecycle/service.py` | `TenantLifecycleService` |
| `src/lexigram/tenancy/isolation/registry.py` | `IsolationStrategyRegistry` |
| `src/lexigram/tenancy/config_overrides/service.py` | `TenantConfigService` |