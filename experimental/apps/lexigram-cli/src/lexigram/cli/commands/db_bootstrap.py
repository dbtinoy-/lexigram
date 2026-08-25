"""Bootstrap helpers shared by the database management commands."""

from __future__ import annotations

import importlib
from typing import Any

import typer

from lexigram.cli.output import OutputManager


async def _bootstrap_migration_runner() -> Any:
    """Used for direct migration execution (run/rollback/status) via the DI container.

    Prefers the DI-managed runner when lexigram-sql is available so that
    connection pooling and observability hooks are active.  Falls back to the
    legacy factory when the package is not installed.
    """
    import os

    db_url = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")

    try:
        from lexigram.contracts.data.sql.migrations import MigrationRunnerProtocol
        from lexigram.di.container import Container
        from lexigram.di.orchestrator import ProviderOrchestrator

        sql_provider_mod = importlib.import_module("lexigram.sql.di.provider")
        DBDIProvider = sql_provider_mod.DatabaseProvider

        container = Container()
        provider = DBDIProvider(config=db_url)
        orchestrator = ProviderOrchestrator(container)
        orchestrator.add(provider)
        await orchestrator.boot_all(container)
        return await container.resolve(MigrationRunnerProtocol)

    except ImportError:
        # lexigram-sql not installed — fall back to legacy direct factory.
        try:
            db_cli = importlib.import_module("lexigram.sql.cli")
            return db_cli.create_cli_migration_manager(db_url)
        except ImportError as e:
            out = OutputManager()
            out.error(
                f"lexigram-sql is required for database commands — install it with: uv add lexigram-sql ({e})"
            )
            raise typer.Exit(1) from None


async def _bootstrap_db_provider() -> tuple[Any, Any]:
    """Used by `db setup` to resolve a DatabaseProviderProtocol outside a full app boot.

    Registers and boots the DatabaseProvider directly against a fresh
    Container via a ProviderOrchestrator (same lifecycle as Application),
    then resolves DatabaseProviderProtocol.

    Returns:
        A ``(db, provider)`` tuple: the resolved database facade and the
        booted DatabaseProvider (so the caller can shut it down afterwards).
    """
    import os

    db_url = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
    try:
        from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
        from lexigram.di.container import Container
        from lexigram.di.orchestrator import ProviderOrchestrator

        sql_provider_mod = importlib.import_module("lexigram.sql.di.provider")
        DatabaseProvider = sql_provider_mod.DatabaseProvider
        sql_config_mod = importlib.import_module("lexigram.sql.config")
        DatabaseConfig = sql_config_mod.DatabaseConfig

        container = Container()
        provider = DatabaseProvider(config=db_url)
        # Satisfy the orchestrator's config-injection phase: the provider
        # already holds an explicit DatabaseConfig, so LexigramConfig lookup
        # (unavailable in this bare CLI container) must be skipped.
        provider.config = DatabaseConfig.from_url(db_url)
        orchestrator = ProviderOrchestrator(container)
        orchestrator.add(provider)
        await orchestrator.boot_all(container)
        return await container.resolve(DatabaseProviderProtocol), provider

    except ImportError as e:
        out = OutputManager()
        out.error(
            f"lexigram-sql is required for database commands — install it with: uv add lexigram-sql ({e})"
        )
        raise typer.Exit(1) from None


async def get_migration_manager() -> Any:
    """Used for introspection/listing: resolves a legacy SimpleMigrationManager exposing the full manager API.

    Commands that only need run/rollback/status should use
    ``_bootstrap_migration_runner()`` to resolve MigrationRunnerProtocol
    through the DI container instead.
    """
    try:
        import os

        db_cli = importlib.import_module("lexigram.sql.cli")
        db_url = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
        return db_cli.create_cli_migration_manager(db_url)
    except ImportError as e:
        out = OutputManager()
        out.error(f"Failed to import lexigram-sql: {e}")
        raise typer.Exit(1) from None


__all__ = [
    "_bootstrap_db_provider",
    "_bootstrap_migration_runner",
    "get_migration_manager",
]
