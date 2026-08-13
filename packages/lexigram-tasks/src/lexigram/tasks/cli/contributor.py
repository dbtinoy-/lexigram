"""Tasks CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    HealthCheckContribution,
    SchemaSetupContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="task",
        title="Generate Task",
        description="Generate a background task with queue registration",
        contributor="tasks",
        generator_path="lexigram.tasks.cli.generators.task:TaskGenerator",
        default_output_dir="src/tasks",
    ),
)


class TasksCliContributor:
    """CLI contributor for the lexigram-tasks package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "tasks"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for tasks."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list[CommandContribution]:
        """Return the contributed `tasks` command group."""
        return [
            CommandContribution(
                name="tasks",
                help="Background task management commands",
                app_factory_path="lexigram.tasks.cli.commands:create_tasks_app",
                contributor="tasks",
                category="extension",
                requires_app_context=True,
            ),
        ]

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return task worker health check."""
        return [
            HealthCheckContribution(
                name="task_worker_status",
                description="Check task worker process is responsive",
                check_path="lexigram.tasks.cli.checks:check_task_worker",
                contributor="tasks",
                category="tasks",
                timeout=5.0,
            ),
        ]

    def get_doctor_checks(self) -> list:
        """Return no doctor checks."""
        return []

    def get_shell_context(self) -> list:
        """Return no shell context contributions."""
        return []

    def get_hooks(self) -> list:
        """Return no hook contributions."""
        return []

    def get_schema_setup(self) -> list[SchemaSetupContribution]:
        """Return schema setup contributions for tasks."""
        return [
            SchemaSetupContribution(
                name="tasks.scheduled_jobs",
                description="Scheduled job storage",
                setup_fn_path="lexigram.tasks.cli.schema_setup:ensure_scheduled_jobs",
                contributor=self.contributor_id,
            ),
            SchemaSetupContribution(
                name="tasks.workflow_states",
                description="Workflow execution state storage",
                setup_fn_path="lexigram.tasks.cli.schema_setup:ensure_workflow_states",
                contributor=self.contributor_id,
            ),
        ]


__all__ = ["TasksCliContributor"]
