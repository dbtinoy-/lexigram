"""Checksum backfill utility for audit entries without checksums."""

from __future__ import annotations

from lexigram.audit.verification.checksum import compute_audit_checksum
from lexigram.logging import get_logger

__all__ = ["backfill_checksums"]

logger = get_logger(__name__)


async def backfill_checksums(
    store: object,
    key: bytes,
    batch_size: int = 100,
    upgrade_schema: bool = False,
) -> int:
    """Compute and populate checksums for entries with NULL checksum.

    When *upgrade_schema* is ``True``, also updates old entries to
    schema version 2 (backfilling ``entry_schema_version`` column).

    Args:
        store: The SQL audit store with direct DB access.
        key: HMAC secret key bytes.
        batch_size: Number of rows to process per batch.
        upgrade_schema: Upgrade old entries to schema version 2.

    Returns:
        Count of entries updated.
    """
    logger.info(
        "audit.backfill_checksums.start",
        batch_size=batch_size,
        upgrade_schema=upgrade_schema,
    )

    store_dict = vars(store) if hasattr(store, "__dict__") else {}
    db = store_dict.get("_db")
    table = store_dict.get("_table", "audit_log")

    if db is None:
        logger.warning("audit.backfill_checksums.no_db")
        return 0

    total_updated = 0
    offset = 0

    while True:
        fetch_sql = (
            f"SELECT * FROM {table} "
            f"WHERE checksum IS NULL "
            f"ORDER BY id ASC "
            f"LIMIT ? OFFSET ?"
        )
        result = await db.execute_query(fetch_sql, [batch_size, offset])
        rows = result.rows if hasattr(result, "rows") else []
        if not rows:
            break

        for row in rows:
            row_dict = dict(row)
            data_for_checksum = {
                k: v
                for k, v in row_dict.items()
                if k not in ("id", "created_at", "checksum")
            }
            current_schema = row_dict.get("entry_schema_version", 1) or 1
            schema_version = 2 if upgrade_schema else current_schema
            checksum = compute_audit_checksum(
                data_for_checksum, key, schema_version=schema_version
            )

            updates = ["checksum = ?"]
            params: list[str | int] = [checksum]
            if upgrade_schema:
                updates.append("entry_schema_version = ?")
                params.append(2)
            params.append(row_dict["id"])

            update_sql = f"UPDATE {table} SET {', '.join(updates)} WHERE id = ?"
            await db.execute_query(update_sql, params)

        total_updated += len(rows)
        offset += batch_size

    logger.info("audit.backfill_checksums.complete", updated=total_updated)
    return total_updated
