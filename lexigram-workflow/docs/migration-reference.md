# Database Migrations for lexigram-workflow

The `DatabaseContentCheckpointStore` auto-creates the `workflow_content_checkpoints`
table on first use via `CREATE TABLE IF NOT EXISTS`. For managed schema migrations
(e.g., via Alembic), use the following as a reference:

## PostgreSQL

```sql
CREATE TABLE IF NOT EXISTS workflow_content_checkpoints (
    key_str TEXT PRIMARY KEY,
    entry_json TEXT NOT NULL,
    stage_handler_version TEXT NOT NULL,
    output_size_bytes INTEGER NOT NULL,
    completed_at TEXT NOT NULL,
    created_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wcc_stage
    ON workflow_content_checkpoints (key_str);
```
