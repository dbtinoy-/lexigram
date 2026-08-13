"""CLI integration utilities for lexigram-sql.

Provides a single, stable factory entry-point for the Lexigram CLI so that
CLI tools do not need to couple to internal class names inside ``lexigram-sql``.
"""

from __future__ import annotations

from lexigram.sql.migrations.manager import SimpleMigrationManager
from lexigram.sql.providers import DatabaseService


def create_cli_migration_manager(
    db_url: str,
    migrations_dir: str | None = None,
) -> SimpleMigrationManager:
    """Create a migration manager configured for CLI usage.

    Constructs a :class:`~lexigram.sql.providers.DatabaseService` and a
    :class:`~lexigram.sql.migrations.manager.SimpleMigrationManager` from
    a database URL.  This is the **single entry-point** for CLI tools that
    need migration management, so they do not have to import internal class
    names from ``lexigram.sql`` directly.

    Args:
        db_url: Database connection URL (e.g. ``sqlite:///./dev.db``).
        migrations_dir: Optional path to the migrations directory.
            Defaults to ``"migrations"`` relative to the current directory.

    Returns:
        A :class:`~lexigram.sql.migrations.manager.SimpleMigrationManager`
        wired to a ``DatabaseService`` for ``db_url``.
    """
    provider = DatabaseService(config=db_url)
    manager = SimpleMigrationManager(
        provider=provider,  # type: ignore[arg-type]
        migrations_dir=migrations_dir,
    )
    provider.migration_manager = manager
    return manager


__all__ = ["create_cli_migration_manager"]
