"""Alembic migration manager implementation.

This module provides migration management capabilities for Lexigram DB.
It supports both Alembic-based migrations (enterprise) and a simple
migration manager (community edition).

Example:
    Using AlembicManager::

        from lexigram.sql.migrations.manager import AlembicManager

        manager = AlembicManager(
            connection_or_provider="postgresql://user:pass@localhost/db",
            migrations_path="./migrations",
        )
        await manager.initialize()
        await manager.upgrade()

    Using SimpleMigrationManager::

        from lexigram.sql.migrations.manager import SimpleMigrationManager

        manager = SimpleMigrationManager(provider=db_provider)
        await manager.initialize_migration_table()
        await manager.apply_migration("001", "create_users", CREATE_USERS_SQL)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from lexigram.contracts import (
    DatabaseProviderProtocol,
    MigrationManagerProtocol,
    MigrationRecord,
)
from lexigram.contracts.data.identifiers import Table
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.sql.exceptions import DatabaseError, QueryError
from lexigram.sql.migrations.engine import MigrationEngine
from lexigram.sql.migrations.introspector import SchemaIntrospector
from lexigram.sql.migrations.orchestrator import MigrationOrchestrator
from lexigram.sql.migrations.types import MigrationInfo, MigrationStatus

logger = get_logger(__name__)

Config: Any = None
ScriptDirectory: Any = None
MigrationContext: Any = None
ALEMBIC_AVAILABLE = False
try:
    from alembic.config import Config

    ALEMBIC_AVAILABLE = True
except ImportError:  # pragma: no cover - availability checked at runtime
    ALEMBIC_AVAILABLE = False


class AlembicManager:
    """Alembic migration manager facade for Lexigram DB.

    Provides a high-level interface for managing database migrations using
    Alembic. Supports upgrade, downgrade, branch creation, and revision
    management.

    Example:
        Initializing and running migrations::

            manager = AlembicManager(
                connection_or_provider=db_provider,
                migrations_path="./migrations",
            )
            await manager.initialize()
            await manager.upgrade("head")
    """

    def __init__(
        self,
        connection_or_provider: Any,
        migrations_path: str | Path | None = None,
        script_location: str | Path | None = None,
        alembic_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the Alembic migration manager.

        Args:
            connection_or_provider: Database connection string or provider instance.
            migrations_path: Path to migrations directory. Defaults to "./migrations".
            script_location: Path to Alembic scripts. Defaults to "migrations/versions".
            alembic_config: Additional Alembic configuration options.

        Raises:
            ImportError: If Alembic is not installed.
        """
        if not ALEMBIC_AVAILABLE:
            raise ImportError("Alembic is not installed.")

        self._provider = None
        if hasattr(connection_or_provider, "url"):
            self._provider = connection_or_provider
            self.database_url = connection_or_provider.url
        else:
            self.database_url = str(connection_or_provider)
        self.connection_string = self.database_url

        self.migrations_path = Path(migrations_path or "migrations")
        self.script_location = (
            Path(script_location)
            if script_location
            else self.migrations_path / "versions"
        )
        self.alembic_config = alembic_config or {}

        # Don't create directories here, let initialize handle it
        # self.migrations_path.mkdir(parents=True, exist_ok=True)
        # Don't create script_location yet, let initialize or Alembic handle it
        # self.script_location.mkdir(parents=True, exist_ok=True)

        self.config = self._create_alembic_config()
        self.engine = MigrationEngine(self.config)
        self.introspector = SchemaIntrospector(self.config, self.connection_string)
        self.orchestrator = MigrationOrchestrator(
            self._provider,
            self.connection_string,
        )
        # Re-entrancy guard: providers boot concurrently, and lazy boot
        # triggers can double-invoke `upgrade("head")` during startup.
        self._upgraded = False

    def _create_alembic_config(self) -> Config:
        """Create and configure Alembic Config object."""
        package_root = Path(__file__).resolve().parents[4]
        config = Config()
        config.config_file_name = str(package_root / "alembic.ini")
        config.set_main_option("script_location", str(self.migrations_path))
        # Strip +aiosqlite/+asyncpg for Alembic which is sync
        self.connection_string = self.database_url
        if "+aiosqlite" in self.connection_string:
            self.connection_string = self.connection_string.replace("+aiosqlite", "")
        elif "+asyncpg" in self.connection_string:
            self.connection_string = self.connection_string.replace("+asyncpg", "")

        config.set_main_option("sqlalchemy.url", self.connection_string)
        config.set_main_option("version_locations", str(self.script_location))
        for key, value in self.alembic_config.items():
            config.set_main_option(key, str(value))
        return config

    async def initialize(self) -> None:
        """Initialize the migration system.

        Creates the migration tracking table and initializes Alembic environment if needed.
        """
        await self.orchestrator.initialize_migration_table()

        # Initialize Alembic if not already done
        if (
            not self.migrations_path.exists()
            or not (self.migrations_path / "env.py").exists()
        ):
            from alembic import command
            from alembic.util.exc import CommandError

            def _init() -> Any:
                try:
                    # If directory exists but is empty, command.init is usually fine
                    # If it's not empty, it might fail.
                    command.init(self.config, str(self.migrations_path))
                except CommandError as e:
                    if "already exists and is not empty" in str(e):
                        logger.warning("Alembic init into non-empty directory: %s", e)
                        # Ensure basic files exist even if init failed due to non-empty dir
                        self.migrations_path.mkdir(parents=True, exist_ok=True)
                    else:
                        raise

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _init)

        # Ensure versions directory exists
        self.script_location.mkdir(parents=True, exist_ok=True)

    async def upgrade(self, revision: str = "head", **kwargs: Any) -> None:
        """Run database migrations up to the specified revision.

        Concurrent invocations (e.g. providers booting in parallel) are
        collapsed into a single migration run.

        Args:
            revision: Target revision. Defaults to "head" (latest).
            **kwargs: Additional arguments passed to Alembic upgrade.
        """
        if self._upgraded:
            return
        self._upgraded = True
        await self.engine.upgrade(revision, **kwargs)

    async def downgrade(self, revision: str = "-1", **kwargs: Any) -> None:
        """Run database migrations down to the specified revision.

        Args:
            revision: Target revision. Defaults to "-1" (previous).
            **kwargs: Additional arguments passed to Alembic downgrade.
        """
        self._upgraded = False
        await self.engine.downgrade(revision, **kwargs)

    async def upgrade_dry_run(self, revision: str = "head") -> list[str]:
        """Preview migrations that would be applied without executing them.

        Args:
            revision: Target revision. Defaults to "head".

        Returns:
            List of SQL statements that would be executed.
        """
        return await self.engine.upgrade_dry_run(revision)

    async def downgrade_dry_run(self, revision: str = "base") -> list[str]:
        """Preview downgrade that would be applied without executing it.

        Args:
            revision: Target revision. Defaults to "base".

        Returns:
            List of SQL statements that would be executed.
        """
        return await self.engine.downgrade_dry_run(revision)

    async def get_status(self) -> MigrationStatus:
        """Get the current migration status.

        Returns:
            MigrationStatus with current state of migrations.
        """
        return await self.introspector.get_status()

    async def get_history(self, limit: int | None = None) -> list[MigrationInfo]:
        """Get the migration history.

        Args:
            limit: Maximum number of migrations to return. None for all.

        Returns:
            List of MigrationInfo objects representing the history.
        """
        return await self.introspector.get_history(limit)

    async def get_branches(self) -> list[dict[str, Any]]:
        """Get available Alembic branches.

        Returns:
            List of branch definitions.
        """
        return await self.introspector.get_branches()

    async def create_revision(self, message: str, **kwargs: Any) -> str:
        """Create a new database migration revision.

        Args:
            message: Revision message/description.
            **kwargs: Additional arguments for revision creation.

        Returns:
            The revision identifier.
        """
        return await self.engine.create_revision(message, **kwargs)

    async def create_initial_revision(self, message: str, **kwargs: Any) -> str:
        """Create the initial database migration revision.

        Args:
            message: Revision message/description.
            **kwargs: Additional arguments for revision creation.

        Returns:
            The revision identifier.
        """
        return await self.create_revision(message, **kwargs)

    async def create_branch(self, branch_name: str, **kwargs: Any) -> str:
        """Create a new Alembic branch.

        Args:
            branch_name: Name of the branch to create.
            **kwargs: Additional arguments.

        Returns:
            The branch revision identifier.
        """
        return await self.engine.create_branch(branch_name, **kwargs)

    async def merge_branches(self, source: str, target: str, **kwargs: Any) -> str:
        """Merge two Alembic branches.

        Args:
            source: Source branch identifier.
            target: Target branch identifier.
            **kwargs: Additional arguments.

        Returns:
            The merged revision identifier.
        """
        return await self.engine.merge_branches(source, target, **kwargs)

    async def stamp(self, revision: str) -> None:
        """Stamp the database with a specific revision without running migrations.

        Args:
            revision: Revision to stamp the database with.
        """
        await self.engine.stamp(revision)  # type: ignore[attr-defined]

    async def edit(self, revision: str) -> None:
        """Edit a revision file in the default editor.

        Args:
            revision: Revision to edit.
        """
        await self.engine.edit(revision)

    async def squash(self, revisions: list[str], message: str) -> str:
        """Squash multiple revisions into a single revision.

        Args:
            revisions: List of revision identifiers to squash.
            message: Message for the new squashed revision.

        Returns:
            The new squashed revision identifier.
        """
        return await self.engine.squash(revisions, message)

    async def validate_migrations(self) -> dict[str, Any]:
        """Validate that applied migrations match the expected state.

        Returns:
            Dictionary with validation results.
        """
        return await self.introspector.validate_migrations()

    async def get_pending_operations(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Get list of pending migration operations.

        Args:
            **kwargs: Additional filtering options.

        Returns:
            List of pending operations with their details.
        """
        return await self.introspector.get_pending_operations(**kwargs)

    async def get_applied_migrations(self) -> list[MigrationRecord]:
        """Return records for all migrations applied up to the current revision.

        Note: Alembic does not natively track applied-at timestamps per
        revision.  Each returned :class:`~lexigram.contracts.MigrationRecord`
        has its ``applied_at`` set to *now* as an approximation.  For precise
        per-migration timestamps, use a custom Alembic event hook that inserts
        into a supplementary audit table.

        Returns:
            List of :class:`~lexigram.contracts.MigrationRecord` for every
            revision that has been stamped at or before the current head.
        """
        status = await self.introspector.get_status()
        if status.current_revision is None:
            return []

        history = await self.introspector.get_history()
        now = ambient_clock.now()
        applied: list[MigrationRecord] = []
        for info in history:
            applied.append(
                MigrationRecord(
                    version=info.version,
                    name=info.description or info.version,
                    applied_at=now,
                    success=True,
                    error_message=None,
                )
            )
            if info.version == status.current_revision:
                break

        return applied

    async def rollback_migration(self, version: str) -> bool:
        """Downgrade the database to *version*, effectively rolling it back.

        Args:
            version: Target Alembic revision string (e.g. ``"-1"``,
                ``"abc123"``).

        Returns:
            ``True`` if the downgrade completed successfully, ``False``
            otherwise.

        Raises:
            DatabaseError: Re-raised if the Alembic downgrade raises a hard
                database error.
        """
        try:
            await self.downgrade(version)
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001 — migration framework may raise non-database exceptions; logged and returns False
            logger.error("rollback_migration_failed", version=version, error=str(exc))
            return False
        else:
            return True

    async def get_pending_migrations(
        self,
        available_migrations: list[str],
    ) -> list[str]:
        """Return the subset of *available_migrations* that have not yet been applied.

        The method intersects the caller-supplied list of revision identifiers
        with Alembic's own pending-migration set derived from the live
        database state.

        Args:
            available_migrations: Ordered list of revision identifiers the
                caller considers "available" (e.g. from a manifest or
                auto-discovery).

        Returns:
            Those identifiers from *available_migrations* that Alembic reports
            as not yet applied.
        """
        status = await self.introspector.get_status()
        pending_revisions = {m.revision for m in status.pending_migrations}
        return [v for v in available_migrations if v in pending_revisions]

    async def initialize_migration_table(self) -> None:
        """Initialize the migration tracking table."""
        await self.orchestrator.initialize_migration_table()

    async def apply_migration(self, version: str, name: str, sql: str) -> bool:
        """Apply a raw SQL migration.

        This method is primarily for compatibility and programmatic application
        of migrations. It handles session management if the provider supports it.

        Args:
            version: Migration version.
            name: Migration name.
            sql: SQL to execute.

        Returns:
            True if successful.

        Raises:
            DatabaseError: If migration fails.
        """
        from lexigram.contracts.exceptions import DatabaseError

        session_cm = None
        if hasattr(self._provider, "session"):
            session_cm = self._provider.session()  # type: ignore[union-attr]

        try:
            if session_cm:
                async with session_cm as session:
                    await session.execute(sql)
                    if hasattr(session, "commit"):
                        await session.commit()
            # Simple provider or connection string fallback
            elif hasattr(self._provider, "execute"):
                await self._provider.execute(sql)  # type: ignore[union-attr]
            else:
                # Last resort fallback to raw execution
                import aiosqlite

                if "sqlite" in str(self.connection_string):
                    path = str(self.connection_string).split("///")[-1].split("://")[-1]
                    async with aiosqlite.connect(path) as conn:
                        await conn.execute(sql)
                        await conn.commit()

            return True
        except (DatabaseError, QueryError, OSError, RuntimeError) as e:
            logger.exception("apply_migration failed")
            if session_cm:
                try:
                    # Some session CMs might not have rollback on the CM itself but on the session
                    # But the tests provide a session-like object that has rollback
                    if hasattr(session_cm, "rollback"):
                        await session_cm.rollback()
                except (DatabaseError, QueryError, OSError, RuntimeError):
                    logger.exception(
                        "Rollback failed during migration apply",
                    )
            raise DatabaseError(f"Migration apply failed: {e}") from e


class SimpleMigrationManager(MigrationManagerProtocol):
    """Simple migration manager for community edition.

    Provides basic migration tracking and execution without advanced
    features like dependency resolution or rollback scripts.

    Example:
        Basic usage::

            manager = SimpleMigrationManager(provider=db_provider)
            await manager.initialize_migration_table()
            await manager.apply_migration("001", "create_users", CREATE_SQL)
    """

    async def create(self, name: str, message: str) -> str:
        """Create a new migration file (alias for create_migration_file).

        Args:
            name: Migration name.
            message: Migration description or SQL content.

        Returns:
            The version string of the created migration.
        """
        return await self.create_migration_file(name, f"-- {message}")

    async def get_current_version(self) -> str | None:
        """Get the version of the most recently applied migration.

        Returns:
            The version string, or None if no migrations have been applied.
        """
        applied = await self.get_applied_migrations()
        if not applied:
            return None
        return applied[-1].version

    def __init__(
        self,
        provider: DatabaseProviderProtocol | None = None,
        migrations_dir: str | None = None,
    ):
        """Initialize the simple migration manager.

        Args:
            provider: Database provider instance.
            migrations_dir: Directory for migration files. Defaults to "./migrations".
        """
        self.provider = provider
        self.migrations_dir = Path(migrations_dir or "migrations")
        self.migration_table = "__migrations"

    async def initialize_migration_table(self) -> None:
        """Initialize the migration tracking table.

        Creates the __migrations table if it doesn't exist.
        """
        if self.provider is None:
            return
        columns = {
            "version": "VARCHAR(255) PRIMARY KEY",
            "name": "VARCHAR(255) NOT NULL",
            "applied_at": "TIMESTAMP NOT NULL",
            "success": "BOOLEAN NOT NULL",
            "error_message": "TEXT",
        }

        if not await self.provider.table_exists(self.migration_table):
            await self.provider.execute(
                f"CREATE TABLE {self.migration_table} ({', '.join(f'{k} {v}' for k, v in columns.items())})",
            )

    async def get_applied_migrations(self) -> list[MigrationRecord]:
        """Get list of applied migrations.

        Returns:
            List of MigrationRecord for all applied migrations.
        """
        if self.provider is None:
            return []

        if not await self.provider.table_exists(self.migration_table):
            return []

        migration_table = Table(self.migration_table)
        result = await self.provider.execute_query(
            f"SELECT version, name, applied_at, success, error_message FROM {migration_table} ORDER BY applied_at",
        )
        return [
            MigrationRecord(
                version=row["version"],
                name=row["name"],
                applied_at=row["applied_at"],
                success=row["success"],
                error_message=row.get("error_message"),
            )
            for row in result.rows
        ]

    async def apply_migration(self, version: str, name: str, sql: str) -> bool:
        """Apply a migration to the database."""
        if self.provider is None:
            return False
        migration_table = Table(self.migration_table)
        applied_at = ambient_clock.now()

        try:
            await self.provider.execute(sql)
            await self.provider.execute(
                f"INSERT INTO {migration_table} (version, name, applied_at, success) VALUES (?, ?, ?, ?)",
                (version, name, applied_at, True),
            )
            logger.info("Applied migration %s: %s", version, name)
            return True
        except (DatabaseError, QueryError, OSError, RuntimeError) as e:
            await self.provider.execute(
                f"INSERT INTO {migration_table} (version, name, applied_at, success, error_message) VALUES (?, ?, ?, ?, ?)",
                (version, name, applied_at, False, str(e)),
            )
            logger.exception("Failed to apply migration %s", version)
            return False

    async def rollback_migration(self, version: str) -> bool:
        """Rollback a migration by removing it from the tracking table.

        Note:
            This only removes the migration record. Actual rollback
            SQL must be executed separately.

        Args:
            version: Migration version to rollback.
        """
        if self.provider is None:
            return False
        migration_table = Table(self.migration_table)
        await self.provider.execute(
            f"DELETE FROM {migration_table} WHERE version = ?",
            (version,),
        )
        logger.info("Rolled back migration %s", version)
        return True

    async def get_pending_migrations(
        self,
        available_migrations: list[str],
    ) -> list[str]:
        """Get migrations that haven't been applied yet."""
        applied = await self.get_applied_migrations()
        applied_versions = {m.version for m in applied if m.success}
        return [v for v in available_migrations if v not in applied_versions]

    async def apply_pending_migrations(self) -> list[str]:
        """Apply all pending migrations in the migrations directory."""
        if not self.migrations_dir.exists():
            return []

        applied_migrations = []
        available_versions = []
        migration_files = {}

        for file in sorted(self.migrations_dir.glob("*.sql")):
            version = file.stem
            available_versions.append(version)
            migration_files[version] = file

        pending_versions = await self.get_pending_migrations(available_versions)

        for version in pending_versions:
            file = migration_files[version]
            sql = file.read_text()

            # Try to extract name from first line comment
            name = f"Migration {version}"
            first_line = sql.splitlines()[0] if sql else ""
            if first_line.startswith("-- "):
                name = first_line[3:].strip()

            await self.apply_migration(version, name, sql)
            applied_migrations.append(version)

        return applied_migrations

    async def create_migration_file(self, name: str, sql: str) -> str:
        """Create a new migration file."""
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        now = ambient_clock.now()
        version = now.strftime("%Y%m%d%H%M%S") if now else "00000000000000"
        file_path = self.migrations_dir / f"{version}.sql"

        content = f"-- {name}\n{sql}\n"
        file_path.write_text(content)

        return version
