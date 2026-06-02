"""Database management commands using registry pattern."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import subprocess
from typing import Annotated

import typer

from lexigram.cli.output import OutputManager
from lexigram.cli.registry import DatabaseConnection
from lexigram.cli.runtime import handle_errors
from lexigram.contracts.cli.contributions import SchemaSetupOutcome, SchemaSetupResult

app = typer.Typer(name="db")


async def _bootstrap_migration_runner():
    """Used for direct migration execution (run/rollback/status) via the DI container.

    Prefers the DI-managed runner when lexigram-sql is available so that
    connection pooling and observability hooks are active.  Falls back to the
    legacy factory when the package is not installed.
    """
    import os

    db_url = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")

    try:
        from lexigram import Container
        from lexigram.contracts.data.sql.migrations import MigrationRunnerProtocol

        sql_provider_mod = importlib.import_module("lexigram.sql.di.provider")
        DBDIProvider = sql_provider_mod.DatabaseService

        container = Container()
        provider = DBDIProvider(config=db_url)
        await container.register(provider)
        await container.boot()
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


async def _bootstrap_db_provider():
    """Used by `db setup` to resolve a DatabaseProviderProtocol outside a full app boot.

    Registers and boots the DatabaseProvider directly against a fresh
    Container, then resolves DatabaseProviderProtocol.

    Returns:
        A ``(db, provider)`` tuple: the resolved database facade and the
        booted DatabaseProvider (so the caller can shut it down afterwards).
    """
    import os

    db_url = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
    try:
        from lexigram import Container
        from lexigram.contracts.data.sql.database import DatabaseProviderProtocol

        sql_provider_mod = importlib.import_module("lexigram.sql.di.provider")
        DatabaseProvider = sql_provider_mod.DatabaseProvider

        container = Container()
        provider = DatabaseProvider(config=db_url)
        await provider.register(container)
        await provider.boot(container)
        return await container.resolve(DatabaseProviderProtocol), provider

    except ImportError as e:
        out = OutputManager()
        out.error(
            f"lexigram-sql is required for database commands — install it with: uv add lexigram-sql ({e})"
        )
        raise typer.Exit(1) from None


async def get_migration_manager():
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


@app.command()
@handle_errors
def init(
    directory: str = typer.Argument("migrations", help="Migration directory"),
):
    """Initialize database migrations."""
    out = OutputManager()
    path = Path(directory)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        out.success(f"Created {directory} directory.")
    else:
        out.warning(f"Directory {directory} already exists.")


@app.command()
@handle_errors
def migrate(
    name: str = typer.Argument(..., help="Migration name"),
):
    """Generate a new migration file."""
    out = OutputManager()

    async def _run():
        manager = await get_migration_manager()
        version = await manager.create_migration(name, "-- Add your SQL here")
        out.success(f"Created migration {version}: {name}")

    asyncio.run(_run())


@app.command()
@handle_errors
def create(
    name: Annotated[
        str, typer.Argument(help="Migration name (e.g. 'add_users_table')")
    ],
    message: Annotated[
        str | None,
        typer.Option("--message", "-m", help="Migration description"),
    ] = None,
) -> None:
    """Create a new empty migration file.

    Args:
        name: Short name for the migration (snake_case).
        message: Optional longer description.
    """
    import asyncio

    out = OutputManager()

    async def _run() -> None:
        try:
            manager = await get_migration_manager()
            result = await manager.create(name=name, message=message or name)
            out.print(f"[green]Created migration:[/green] {result}")
        except Exception as exc:  # noqa: BLE001
            out.print(f"[red]Failed to create migration: {exc}[/red]")
            raise typer.Exit(1) from exc

    asyncio.run(_run())


@app.command()
@handle_errors
def upgrade(
    env: str | None = typer.Option("--env", "-e", help="Environment name"),
):
    """Apply pending migrations."""
    out = OutputManager()

    async def _run():
        runner = await _bootstrap_migration_runner()
        applied = await runner.run_migrations()
        if applied:
            for v in applied:
                out.success(f"Applied {v}")
        else:
            out.info("No pending migrations.")

    asyncio.run(_run())


@app.command()
@handle_errors
def downgrade(
    version: str | None = typer.Argument(None, help="Version to downgrade to"),
    env: str | None = typer.Option("--env", "-e", help="Environment name"),
):
    """Revert migrations."""
    out = OutputManager()

    async def _run():
        runner = await _bootstrap_migration_runner()
        current = await runner.get_current_version()
        if not current:
            out.info("No migrations to rollback.")
            return

        target = version  # None = roll back most recent
        out.info(f"Rolling back to: {target or 'previous'}")
        rolled_back = await runner.rollback(target)
        if rolled_back:
            for v in rolled_back:
                out.success(f"Rolled back {v}")
        else:
            out.error("Rollback failed or version not found.")

    asyncio.run(_run())


@app.command()
@handle_errors
def status(
    env: str | None = typer.Option("--env", "-e", help="Environment name"),
):
    """Show migration status."""
    out = OutputManager()

    async def _run():
        runner = await _bootstrap_migration_runner()
        current = await runner.get_current_version()
        pending = await runner.get_pending_migrations()

        if current:
            out.print(f"[green]Current version:[/green] {current}")
        else:
            out.warning("No migrations applied yet.")

        if pending:
            out.warning(f"\nPending migrations: {len(pending)}")
            for p in pending:
                out.print(f"  ? {p}")
        else:
            out.print("[green]Schema is up to date.[/green]")

    asyncio.run(_run())


@app.command()
@handle_errors
def history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of migrations to show"),
    env: str | None = typer.Option("--env", "-e", help="Environment name"),
):
    """Show migration history."""
    out = OutputManager()

    async def _run():
        manager = await get_migration_manager()
        await manager.provider.boot()
        try:
            applied = await manager.get_applied_migrations()
            if not applied:
                out.info("No migration history found.")
                return

            out.print(f"[bold]Migration History (last {limit}):[/bold]")
            for _i, m in enumerate(reversed(applied[-limit:])):
                status_icon = "[green]↑[/green]" if m.success else "[red]↓[/red]"
                out.print(f"{status_icon} {m.version} - {m.name}")
        finally:
            await manager.provider.shutdown()

    asyncio.run(_run())


@app.command()
@handle_errors
def validate(
    env: str | None = typer.Option("--env", "-e", help="Environment name"),
):
    """Validate migrations."""
    out = OutputManager()

    async def _run():
        manager = await get_migration_manager()
        await manager.provider.boot()
        try:
            await manager.initialize_migration_table()
            applied = await manager.get_applied_migrations()

            issues: list[str] = []

            if not manager.migrations_dir.exists():
                issues.append("Migrations directory does not exist")

            available = []
            if manager.migrations_dir.exists():
                available = sorted(
                    [
                        f.stem
                        for f in manager.migrations_dir.glob("*.sql")
                        if not f.name.endswith(".down.sql")
                    ],
                )

            {m.version for m in applied}
            for m in applied:
                if m.version not in available and m.version != "init":
                    issues.append(
                        f"Applied migration '{m.version}' has no corresponding file",
                    )

            if issues:
                out.error("Migration validation failed:")
                for issue in issues:
                    out.print(f"  • {issue}")
                raise typer.Exit(1)
            out.success("Migration validation passed!")
            out.print(f"  Applied migrations: {len(applied)}")
            out.print(f"  Available migrations: {len(available)}")
        finally:
            await manager.provider.shutdown()

    asyncio.run(_run())


@app.command()
@handle_errors
def seed(
    file: str | None = typer.Argument(None, help="Specific seed file to run"),
    env: str | None = typer.Option("--env", "-e", help="Environment name"),
):
    """Run database seeders."""
    out = OutputManager()

    async def _run():
        manager = await get_migration_manager()
        await manager.provider.boot()
        try:
            seeds_dir = Path("seeds")
            if not seeds_dir.exists() and not file:
                out.warning("No seeds directory found.")
                return

            files_to_run = []
            if file:
                files_to_run.append(Path(file))
            else:
                files_to_run = sorted(seeds_dir.glob("*.py"))

            for seed_file in files_to_run:
                out.info(f"Running seeder: {seed_file}")

                spec = importlib.util.spec_from_file_location("seed_module", seed_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    if hasattr(module, "run"):
                        if asyncio.iscoroutinefunction(module.run):
                            await module.run(manager.provider)
                        else:
                            module.run(manager.provider)
                        out.success(f"Seeder {seed_file} completed.")
                    else:
                        out.warning(f"No 'run' function found in {seed_file}")

        except (ImportError, RuntimeError, OSError, ValueError, AttributeError) as e:
            out.error(f"Seeder failed: {e}")
            raise typer.Exit(1) from None
        finally:
            await manager.provider.shutdown()

    asyncio.run(_run())


@app.command()
@handle_errors
def reset(
    seed: bool = typer.Option(False, "--seed", help="Run seeders after reset"),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force reset without confirmation",
    ),
    env: str | None = typer.Option("--env", "-e", help="Environment name"),
):
    """Drop and recreate the database."""
    out = OutputManager()
    if not force:
        confirm = typer.confirm(
            "Are you sure you want to reset the database? This will delete ALL data.",
        )
        if not confirm:
            raise typer.Abort

    async def _run():
        manager = await get_migration_manager()
        await manager.provider.boot()
        try:
            out.info("Resetting database...")

            if "sqlite" in str(manager.provider.url):
                res = await manager.provider.execute_query(
                    "SELECT name FROM sqlite_master WHERE type='table'",
                )
                tables = [row["name"] for row in res.rows]
                for table in tables:
                    if table != "sqlite_sequence":
                        out.print(f"[dim]Dropping table: {table}[/dim]")
                        await manager.provider.execute(f"DROP TABLE {table}")
            else:
                out.warning(
                    "Reset is only fully optimized for SQLite currently.",
                )

            out.success("Database cleared.")

            await manager.initialize_migration_table()
            applied = await manager.apply_pending_migrations()
            if applied:
                for v in applied:
                    out.success(f"Applied {v}")
            else:
                out.info("No pending migrations.")

            if seed:
                seeds_dir = Path("seeds")
                if seeds_dir.exists():
                    files_to_run = sorted(seeds_dir.glob("*.py"))
                    for seed_file in files_to_run:
                        out.info(f"Running seeder: {seed_file}")

                        spec = importlib.util.spec_from_file_location(
                            "seed_module",
                            seed_file,
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            if hasattr(module, "run"):
                                if asyncio.iscoroutinefunction(module.run):
                                    await module.run(manager.provider)
                                else:
                                    module.run(manager.provider)
                                out.success(f"Seeder {seed_file} completed.")
                else:
                    out.warning("No seeds directory found, skipping seed step.")

        except (RuntimeError, OSError, ValueError, ConnectionError) as e:
            out.error(f"Reset failed: {e}")
            raise typer.Exit(1) from None
        finally:
            await manager.provider.shutdown()

    asyncio.run(_run())


@app.command(name="shell")
@handle_errors
def shell(
    env: str | None = typer.Option("--env", "-e", help="Environment name"),
):
    """Open database shell (auto-detects database type)."""
    out = OutputManager()

    try:
        conn = DatabaseConnection()
        backend = conn.backend

        client_binary = backend.get_client_binary()
        if not client_binary:
            backend_name = backend.name
            out.error(
                f"Client for '{backend_name}' not found.",
                hint=f"Install the {backend_name} client (e.g., sudo apt install {backend_name}-client)",
            )
            raise typer.Exit(1)

        out.info(f"Opening {backend.name} shell...")
        conn.open_shell()

    except (RuntimeError, OSError, AttributeError, LookupError) as e:
        out.error(f"Failed to open shell: {e}")
        raise typer.Exit(1) from None


@app.command(name="inspect")
@handle_errors
def inspect_(
    table: str | None = typer.Option(
        None, "--table", "-t", help="Specific table to inspect"
    ),
    env: str | None = typer.Option(None, "--env", "-e", help="Environment name"),
):
    """Show database schema."""
    out = OutputManager()

    async def _run():
        try:
            conn = DatabaseConnection()

            async with conn:
                if table:
                    columns = await conn.get_columns(table)
                    out.print(f"[bold]Columns in {table}:[/bold]")
                    rows = [
                        [col["name"], col["type"], str(col.get("default", ""))]
                        for col in columns
                    ]
                    out.table(["Column", "Type", "Default"], rows)
                else:
                    tables = await conn.get_tables()
                    if not tables:
                        out.info("No tables found in database.")
                        return
                    out.print("[bold]Tables:[/bold]")
                    for t in tables:
                        out.print(f"  - {t}")

                    out.print("\n[bold]Schema Details:[/bold]")
                    for t in tables:
                        columns = await conn.get_columns(t)
                        out.print(f"\n[cyan]{t}[/cyan]")
                        rows = [
                            [
                                col["name"],
                                col["type"],
                                "YES" if col["nullable"] else "NO",
                            ]
                            for col in columns
                        ]
                        out.table(["Column", "Type", "Nullable"], rows)

        except ImportError as e:
            out.error(f"lexigram-sql not installed: {e}")
            out.info("Install with: pip install lexigram-sql")
            raise typer.Exit(1) from None
        except (RuntimeError, OSError, AttributeError, LookupError) as e:
            out.error(f"Failed to inspect database: {e}")
            raise typer.Exit(1) from None

    asyncio.run(_run())


@app.command(name="backup")
@handle_errors
def backup(
    output: str | None = typer.Option("--output", "-o", help="Output file path"),
    env: str | None = typer.Option("--env", "-e", help="Environment name"),
):
    """Backup the database."""
    out = OutputManager()

    try:
        conn = DatabaseConnection()
        backend = conn.backend

        client_binary = backend.get_client_binary()
        if not client_binary:
            backend_name = backend.name
            out.error(f"Backup not supported for {backend_name}")
            raise typer.Exit(1)

        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_output = f"backup_{backend.name}_{timestamp}.sql"
        output_path = output or default_output

        try:
            # Use registry pattern to build backup command
            cmd = backend.build_backup_command(conn.params, output_path)
            out.info(f"Backing up {backend.name} database to {output_path}...")

            subprocess.run(cmd, check=True)
            out.success(f"Database backed up to {output_path}")
        except subprocess.CalledProcessError as e:
            out.error(f"Backup failed: {e}")
            raise typer.Exit(1) from None
        except RuntimeError as e:
            out.error(str(e))
            raise typer.Exit(1) from None

    except (RuntimeError, OSError, AttributeError, LookupError) as e:
        out.error(f"Failed to backup database: {e}")
        raise typer.Exit(1) from None


@app.command(name="restore")
@handle_errors
def restore(
    input_path: str = typer.Argument(..., help="Backup file to restore"),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force restore without confirmation",
    ),
    env: str | None = typer.Option("--env", "-e", help="Environment name"),
):
    """Restore the database from backup."""
    out = OutputManager()
    if not force:
        confirm = typer.confirm(
            "Are you sure you want to restore the database? This will overwrite all data.",
        )
        if not confirm:
            raise typer.Abort

    backup_path = Path(input_path)
    if not backup_path.exists():
        out.error(f"Backup file not found: {input_path}")
        raise typer.Exit(1)

    try:
        conn = DatabaseConnection()
        backend = conn.backend

        client_binary = backend.get_client_binary()
        if not client_binary:
            backend_name = backend.name
            out.error(f"Restore not supported for {backend_name}")
            raise typer.Exit(1)

        # Use registry pattern to build restore command
        cmd = backend.build_restore_command(conn.params, input_path)

        out.info(f"Restoring {backend.name} database from {input_path}...")

        with open(input_path) as f:
            subprocess.run(cmd, stdin=f, check=True)

        out.success(f"Database restored from {input_path}")

    except subprocess.CalledProcessError as e:
        out.error(f"Restore failed: {e}")
        raise typer.Exit(1) from None
    except (RuntimeError, OSError, AttributeError, LookupError) as e:
        out.error(f"Failed to restore database: {e}")
        raise typer.Exit(1) from None


@app.command()
@handle_errors
def setup(
    package: Annotated[
        str | None,
        typer.Option(
            "--package", help="Only run setup for this package's contributions."
        ),
    ] = None,
) -> None:
    """Run schema setup for all installed packages that need database tables."""
    asyncio.run(_run_setup(package))


async def _run_setup(package: str | None) -> None:
    from lexigram.cli.contributors.runtime import ContributorRuntime

    out = OutputManager()
    runtime = ContributorRuntime.from_entry_points()
    contributions = runtime.schema_setups
    if package:
        contributions = [c for c in contributions if c.name.split(".")[0] == package]

    if not contributions:
        out.info("Nothing to do — no schema setup contributions discovered.")
        return

    db, provider = await _bootstrap_db_provider()

    try:
        for contribution in contributions:
            outcome = await _run_one_schema_setup(contribution, db)
            if outcome.status == SchemaSetupResult.CREATED:
                out.success(f"{contribution.name}: created")
            elif outcome.status == SchemaSetupResult.ALREADY_PRESENT:
                out.info(f"{contribution.name}: already present")
            else:
                out.error(f"{contribution.name}: failed — {outcome.message}")
    finally:
        await provider.shutdown()


async def _run_one_schema_setup(contribution, db) -> SchemaSetupOutcome:
    try:
        module_path, _, fn_name = contribution.setup_fn_path.partition(":")
        mod = importlib.import_module(module_path)
        ensure_fn = getattr(mod, fn_name)
        return await ensure_fn(db)
    except Exception as exc:
        return SchemaSetupOutcome(status=SchemaSetupResult.FAILED, message=str(exc))


__all__ = ["app"]
