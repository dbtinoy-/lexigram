# Lexigram Example: Multi-Tenant SaaS Platform

A reference application demonstrating how to build a multi-tenant SaaS platform
using the Lexigram framework. This example covers:

- **Multi-tenancy** — tenant lifecycle management (create, suspend) with aggregate
  roots recording domain events.
- **RBAC** — role-based access control via a pure, registry-backed `can_access`
  function. No `if/elif` chains.
- **Feature flags** — per-context flag evaluation using `lexigram-features`
  `FlagManager` with a `LocalProvider`.
- **Domain events** — `TenantCreated`, `TenantSuspended`, `UserInvited`, and
  `RoleChanged` events flowing through the `EventBusProtocol`.
- **Result pattern** — every domain operation returns `Result[T, E]`; callers
  always check `is_ok()` before `unwrap()`.
- **Constructor injection** — services receive all dependencies via `__init__`;
  nothing is resolved from the container inside business logic.

## Architecture

```
lexigram_example_platform/
├── domain/          # Aggregates, entities, value objects, events — zero deps
├── repositories/    # Protocols + in-memory implementations
├── services/        # Application services: Result-returning use-case handlers
├── admin/           # Admin dashboard contributor
└── di/              # PlatformProvider: composition root
```

## Running

```bash
# From the lexigram monorepo root
uv run python -m lexigram_example_platform.main
```

## Tests

```bash
cd examples/platform
uv run pytest --tb=short
uv run pytest --cov=lexigram_example_platform --cov-fail-under=80
```

## Key Patterns Demonstrated

### Result pattern
```python
result = await tenant_service.create_tenant(name="Acme", slug="acme")
if result.is_ok():
    tenant = result.unwrap()
else:
    error = result.unwrap_err()
```

### RBAC policy
```python
from lexigram_example_platform.domain.policy import can_access
from lexigram_example_platform.domain.membership import Role

assert can_access(Role.OWNER, "billing", "delete") is True
assert can_access(Role.VIEWER, "billing", "delete") is False
```

### Feature flags
```python
from lexigram.features.types import Flag, FlagType, FlagContext

flag = Flag(name="advanced_analytics", type=FlagType.BOOLEAN, enabled=True)
ctx = FlagContext(user_id="user-1", attributes={"tenant_id": "t-1"})
evaluation = await flag_manager.evaluate("advanced_analytics", ctx)
```
