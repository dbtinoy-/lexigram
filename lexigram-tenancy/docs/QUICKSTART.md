---
title: lexigram-tenancy Quickstart
description: Install, configure, and resolve your first tenant in under 5 minutes
---

Install the package:

```bash
uv add lexigram-tenancy
```

## Minimal example

```python
import asyncio
from lexigram.app import Application
from lexigram.tenancy import TenancyModule, TenancyConfig


async def main() -> None:
    config = TenancyConfig()
    app = Application(name="my-app")
    app.add_module(TenancyModule.configure(config=config))
    async with Application.boot(name="my-app", modules=[TenancyModule.configure(config=config)]) as app:
        from lexigram.contracts.tenancy.protocols import TenantProviderProtocol

        provider = await app.container.resolve(TenantProviderProtocol)
        result = await provider.create_tenant(
            CreateTenantCommand(slug="acme", name="ACME Corp")
        )
        if result.is_ok():
            tenant = result.unwrap()
            print(f"Created tenant: {tenant.tenant_id}")


asyncio.run(main())
```

## What just happened

- `TenancyModule.configure()` registered the tenancy provider stack (resolution chain, validator, lifecycle service, isolation strategies)
- The `TenantProviderProtocol` was resolved from the container — backed by `InMemoryTenantProvider` by default
- A tenant was created with slug `acme` and name `ACME Corp`

## Next steps

- [Guide](./GUIDE.md) — mental model, resolution chain, isolation strategies
- [Architecture](./ARCHITECTURE.md) — provider composition, contracts, lifecycle
- [Configuration](./CONFIGURATION.md) — resolver order, TTLs, integration toggles
- [How-Tos](./HOWTOS.md) — custom resolvers, SQL backend, per-tenant config overrides
