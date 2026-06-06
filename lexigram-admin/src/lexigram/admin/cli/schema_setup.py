"""Schema setup contributions for the lexigram-admin package."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import SchemaSetupOutcome, SchemaSetupResult
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol


async def ensure_tenant_configs(db: DatabaseProviderProtocol) -> SchemaSetupOutcome:
    """Ensure the ``tenant_configs`` settings table exists.

    Args:
        db: The database provider.

    Returns:
        Outcome reporting CREATED, ALREADY_PRESENT, or FAILED.
    """
    from lexigram.admin.services.settings_service import _TABLE, AdminSettingsDbProvider

    try:
        existed = await db.table_exists(_TABLE)
        await AdminSettingsDbProvider(db)._ensure_table()
        return SchemaSetupOutcome(
            status=(
                SchemaSetupResult.ALREADY_PRESENT
                if existed
                else SchemaSetupResult.CREATED
            )
        )
    except Exception as exc:
        return SchemaSetupOutcome(status=SchemaSetupResult.FAILED, message=str(exc))
