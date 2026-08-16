"""Schema setup contributions for the lexigram-resilience package."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import SchemaSetupOutcome, SchemaSetupResult
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol

_IDEMPOTENCY_TABLE = "idempotency_keys"


async def ensure_idempotency_keys(db: DatabaseProviderProtocol) -> SchemaSetupOutcome:
    """Ensure the ``idempotency_keys`` table exists.

    Args:
        db: The database provider.

    Returns:
        Outcome reporting CREATED, ALREADY_PRESENT, or FAILED.
    """
    from lexigram.resilience.idempotency.database import DatabaseIdempotencyStore

    try:
        existed = await db.table_exists(_IDEMPOTENCY_TABLE)
        await DatabaseIdempotencyStore(db)._ensure_table()
        return SchemaSetupOutcome(
            status=(
                SchemaSetupResult.ALREADY_PRESENT
                if existed
                else SchemaSetupResult.CREATED
            )
        )
    except Exception as exc:
        return SchemaSetupOutcome(status=SchemaSetupResult.FAILED, message=str(exc))
