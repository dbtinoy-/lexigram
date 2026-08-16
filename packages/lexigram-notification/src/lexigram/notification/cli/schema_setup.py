"""Schema setup contributions for the lexigram-notification package."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import SchemaSetupOutcome, SchemaSetupResult
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol

_INBOX_TABLE = "notification_inbox_messages"


async def ensure_inbox_messages(db: DatabaseProviderProtocol) -> SchemaSetupOutcome:
    """Ensure the ``notification_inbox_messages`` table exists.

    Args:
        db: The database provider.

    Returns:
        Outcome reporting CREATED, ALREADY_PRESENT, or FAILED.
    """
    from lexigram.notification.inbox.database import DatabaseInboxStore

    try:
        existed = await db.table_exists(_INBOX_TABLE)
        await DatabaseInboxStore(db)._ensure_table()
        return SchemaSetupOutcome(
            status=(
                SchemaSetupResult.ALREADY_PRESENT
                if existed
                else SchemaSetupResult.CREATED
            )
        )
    except Exception as exc:
        return SchemaSetupOutcome(status=SchemaSetupResult.FAILED, message=str(exc))
