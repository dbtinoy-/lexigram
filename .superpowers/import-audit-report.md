# Import Audit Report (2026-08-27)

## Test Cross-Imports (Low Priority)

14 test files import directly from another extension package.
These are test-only and do not affect production code.

| Source Package | Target Package | File | Line | Import |
|---|---|---|---|---|
| lexigram-sql | lexigram-cache | tests/unit/test_redis_secrets.py | 6 | `from lexigram.cache.stores.redis_secrets import ...` |
| lexigram-sql | lexigram-cache | tests/unit/test_redis_lock.py | 6 | `from lexigram.cache.stores.redis_lock import ...` |
| lexigram-sql | lexigram-cache | tests/unit/test_redis_state.py | 6 | `from lexigram.cache.stores.redis_state import ...` |
| lexigram-sql | lexigram-search | tests/unit/test_db_search_backends.py | 14-15 | `from lexigram.search.backends.mysql/postgres import ...` |
| lexigram-sql | lexigram-search | tests/unit/test_db_search_backends.py | 321 | `from lexigram.search.types import SearchResponse` |
| lexigram-web | lexigram-graphql | tests/unit/test_serializer_injection.py | 9 | `from lexigram.graphql.security.rate_limit import ...` |
| lexigram-events | lexigram-monitor | tests/unit/test_event_bus_tracing.py | 10 | `from lexigram.monitor.tracing import Span, Tracer` |
| lexigram-http | lexigram-resilience | tests/unit/test_http_module_client.py | 282 | `from lexigram.resilience import RetryExhaustedError` |
| lexigram-tasks | lexigram-resilience | tests/unit/test_tasks_features.py | 12 | `from lexigram.resilience.rate_limiter import RateLimiter` |
| lexigram-monitor | lexigram-tasks | tests/unit/test_slo_worker.py | 13 | `from lexigram.tasks.background_task_manager import ...` |
| lexigram-graphql | lexigram-web | tests/unit/test_web_contributor.py | 64 | `from lexigram.web.integrations.graphql import ...` |
| lexigram-tenancy | lexigram-sql | tests/unit/integration/test_sql_bridge.py | 94 | `from lexigram.sql.context import create_db_context` |
| lexigram-tenancy | lexigram-workflow | tests/unit/migration/test_saga.py | 15 | `from lexigram.workflow.checkpoint.store_memory import ...` |
| lexigram-tenancy | lexigram-workflow | tests/unit/migration/test_service.py | 17 | `from lexigram.workflow.checkpoint.store_memory import ...` |
| lexigram-tenancy | lexigram-workflow | tests/unit/migration/test_chaos.py | 15 | `from lexigram.workflow.checkpoint.store_memory import ...` |

## Legitimate Re-Exports (No Action Needed)

- `lexigram.security.protocols` → `lexigram.contracts.ai.exceptions.GuardError`: Re-export bridge for convenience.
- `lexigram-auth` → `lexigram.contracts.ai.relay.*`: Auth package uses relay contracts for DI registration.
- `lexigram-auth` → `lexigram.contracts.ai.session.SessionManagerProtocol`: Session manager DI binding.

## Architecture Confirmation

The "532 experimental files bypass contracts" finding (lexigram.logging, lexigram.di) is a FALSE POSITIVE.
Extensions correctly import from core/lexigram (implementation layer) for concrete functions like `get_logger()`,
`Provider`, `Module`, `DynamicModule`, `inject`. The contracts define protocols; the core implements them;
extensions consume both. This matches the documented three-tier architecture.

## Depth Gate Summary

`make lint-depth` enforces max depth 6 for source files. Allowlisted structural exceptions:
- Contracts relay DTOs (internal re-export wiring)
- DI compiler phases (architectural layering)
- Contracts `__init__.py` re-exports from deep submodules
- Admin UI component re-exports
- UI component re-exports
- AI docs/tools demo wiring
- Relay gateway route re-exports

7 test-only depth violations remain (intra-package test imports) — correctly excluded by default.
