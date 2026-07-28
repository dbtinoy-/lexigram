"""SQL CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    DoctorCheckContribution,
    HealthCheckContribution,
    ShellContextContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="repository",
        title="Generate Repository",
        description="Generate a database repository with query methods",
        contributor="sql",
        generator_path="lexigram.sql.cli.generators.database_repository:DatabaseRepositoryGenerator",
        default_output_dir="src/repositories",
        category="database",
    ),
    GeneratorDefinition(
        name="filter",
        title="Generate Filter",
        description="Generate a query filter for database models",
        contributor="sql",
        generator_path="lexigram.sql.cli.generators.filter:FilterGenerator",
        default_output_dir="src/filters",
        category="database",
    ),
    GeneratorDefinition(
        name="seeder",
        title="Generate Seeder",
        description="Generate a database seeder for test/dev data",
        contributor="sql",
        generator_path="lexigram.sql.cli.generators.seeder:SeederGenerator",
        default_output_dir="seeds",
        category="database",
    ),
    GeneratorDefinition(
        name="health",
        title="Generate Health Check",
        description="Generate a database health check",
        contributor="sql",
        generator_path="lexigram.sql.cli.generators.health_check:HealthCheckGenerator",
        default_output_dir="src/health",
        category="database",
    ),
    GeneratorDefinition(
        name="model",
        title="Generate Model",
        description="Generate a SQLAlchemy model",
        contributor="sql",
        generator_path="lexigram.sql.cli.generators.model:ModelGenerator",
        default_output_dir="src/models",
        category="database",
    ),
    GeneratorDefinition(
        name="service",
        title="Generate Service",
        description="Generate a service with unit of work",
        contributor="sql",
        generator_path="lexigram.sql.cli.generators.service:ServiceGenerator",
        default_output_dir="src/services",
        category="database",
    ),
)


class SqlCliContributor:
    """CLI contributor for the lexigram-sql package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "sql"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for SQL."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list[CommandContribution]:
        """Return the contributed `db` command group."""
        return [
            CommandContribution(
                name="db",
                help="Database migration and management commands",
                app_factory_path="lexigram.sql.cli.commands:create_db_app",
                contributor="sql",
                category="database",
                requires_app_context=False,
            ),
        ]

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return database connectivity health check."""
        return [
            HealthCheckContribution(
                name="database_connection",
                description="Verify database connectivity and migration status",
                check_path="lexigram.sql.cli.checks:check_database_connection",
                contributor="sql",
                category="database",
                timeout=15.0,
                critical=True,
            ),
        ]

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return database configuration doctor checks."""
        return [
            DoctorCheckContribution(
                name="database_url_configured",
                description="Check DATABASE_URL or application.yaml database config exists",
                check_path="lexigram.sql.cli.doctor:check_database_url",
                contributor="sql",
                category="database",
            ),
            DoctorCheckContribution(
                name="migrations_dir_exists",
                description="Check migrations directory exists with valid structure",
                check_path="lexigram.sql.cli.doctor:check_migrations_dir",
                contributor="sql",
                category="database",
                can_fix=True,
            ),
        ]

    def get_shell_context(self) -> list[ShellContextContribution]:
        """Return database shell context contributions."""
        return [
            ShellContextContribution(
                name="db",
                description="Database provider for interactive queries",
                factory_path="lexigram.sql.cli.shell:provide_db",
                contributor="sql",
            ),
            ShellContextContribution(
                name="migration",
                description="Migration runner for interactive use",
                factory_path="lexigram.sql.cli.shell:provide_migration",
                contributor="sql",
            ),
        ]

    def get_hooks(self) -> list:
        """Return no hook contributions."""
        return []


__all__ = ["SqlCliContributor"]
