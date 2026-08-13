# Tier Migration

Content-addressed saga for migrating a tenant between isolation tiers
(row-level → schema → database) with automatic rollback on failure.

## Quick Start

```python
from lexigram.tenancy.migration import TenantTierMigrationSaga

saga = TenantTierMigrationSaga(
    tenant_id="tenant-abc",
    target_tier="m5",
    checkpoint_store=checkpoint_store,
    isolation_registry=registry,
    tenant_provider=provider,
    config_service=config_service,
    write_pause_registry=write_pause,
    copy_strategy=copy_strategy,
)

result = await saga.execute()
if result.is_ok():
    print("Migration complete")
```

## Stages

| # | Stage | Side Effects | Compensation |
|---|-------|-------------|--------------|
| 1 | `validate` | None | None |
| 2 | `provision_target` | Create target isolation (schema/db) | Deprovision target |
| 3 | `copy_data` | Copy tenant data | Rollback copy |
| 4 | `pause_writes` | Block write operations | Resume writes |
| 5 | `set_strategy` | Switch tenant to target strategy | Restore origin strategy |
| 6 | `validate_cutover` | Verify strategy switch | None |
| 7 | `resume_writes` | Unblock write operations | N/A |
| 8 | `deprovision_source` | Remove source isolation | None |
| 9 | `update_tier_config` | Persist new tier to config | None |
| 10 | `cleanup` | Emit checkpoint event | None |

On any stage failure, all completed stages are compensated in reverse
order based on the checkpointed state — partial mutations are fully
rolled back.

## Resume

Stages are **content-addressed**: the saga computes a
`sha256(stage_id || tenant_id || inputs || handler_version)` key per
stage. On resume after a crash, completed stages return cached output
without re-executing. Only the failed stage and subsequent stages run.

## Copy Strategies

| Strategy | Source | Target |
|----------|--------|--------|
| `RowToSchemaCopy` | `row_level` | `schema` |
| `SchemaToRowCopy` | `schema` | `row_level` |
| `SchemaToDatabaseCopy` | `schema` | `database` |
| `DatabaseToSchemaCopy` | `database` | `schema` |

Each strategy delegates to an optional `CopyHandler` callable:

```python
async def my_copy_handler(tenant_id: str, ctx: MigrationContext) -> CopyResult:
    # your data migration logic
    return CopyResult(records_copied=100, records_failed=0)


strategy = RowToSchemaCopy(copy_handler=my_copy_handler)
```

## Content-Addressed Checkpoint Store

The saga persists checkpoint entries to any
`ContentCheckpointStoreProtocol`. Use `InMemoryContentCheckpointStore`
for testing, or implement the protocol for production backends (Redis,
PostgreSQL, etc.).

## See Also

- `lexigram.tenancy.migration.saga` — saga orchestration
- `lexigram.tenancy.migration.copy` — copy strategies
- `lexigram.tenancy.migration.write_pause` — write coordination
- `lexigram.tenancy.migration.service` — migration service facade
