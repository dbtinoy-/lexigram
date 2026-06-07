"""Schema setup contributions for the lexigram-ai-session package."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import SchemaSetupOutcome, SchemaSetupResult
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol

_SESSIONS_TABLE = "ai_sessions"


async def ensure_session_tables(db: DatabaseProviderProtocol) -> SchemaSetupOutcome:
    """Ensure the ``ai_sessions`` and ``ai_checkpoints`` tables exist.

    Args:
        db: The database provider.

    Returns:
        Outcome reporting CREATED, ALREADY_PRESENT, or FAILED.
    """
    from lexigram.ai.session.stores.database import DatabaseSessionStore

    try:
        existed = await db.table_exists(_SESSIONS_TABLE)
        await DatabaseSessionStore(db)._ensure_tables()
        return SchemaSetupOutcome(
            status=(
                SchemaSetupResult.ALREADY_PRESENT
                if existed
                else SchemaSetupResult.CREATED
            )
        )
    except Exception as exc:
        return SchemaSetupOutcome(status=SchemaSetupResult.FAILED, message=str(exc))
