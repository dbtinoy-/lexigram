"""Schema setup contributions for the lexigram-events package."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import SchemaSetupOutcome, SchemaSetupResult
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol

_SAGA_TABLE = "saga_records"


async def ensure_saga_records(db: DatabaseProviderProtocol) -> SchemaSetupOutcome:
    """Ensure the ``saga_records`` table exists.

    Args:
        db: The database provider.

    Returns:
        Outcome reporting CREATED, ALREADY_PRESENT, or FAILED.
    """
    from lexigram.events.sagas.sql import SqlSagaStore

    try:
        existed = await db.table_exists(_SAGA_TABLE)
        await SqlSagaStore(db).initialize()
        return SchemaSetupOutcome(
            status=(
                SchemaSetupResult.ALREADY_PRESENT
                if existed
                else SchemaSetupResult.CREATED
            )
        )
    except Exception as exc:
        return SchemaSetupOutcome(status=SchemaSetupResult.FAILED, message=str(exc))
