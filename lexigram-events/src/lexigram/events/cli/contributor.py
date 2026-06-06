"""Events CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    DoctorCheckContribution,
    HealthCheckContribution,
    SchemaSetupContribution,
    ShellContextContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="event_handler",
        title="Generate Event Handler",
        description="Generate an event handler with bus registration",
        contributor="events",
        generator_path="lexigram.events.cli.generators.event_handler:EventHandlerGenerator",
        default_output_dir="src/handlers",
        category="events",
    ),
    GeneratorDefinition(
        name="saga",
        title="Generate Saga",
        description="Generate a saga orchestrator with compensating actions",
        contributor="events",
        generator_path="lexigram.events.cli.generators.saga:SagaGenerator",
        default_output_dir="src/sagas",
        category="events",
    ),
    GeneratorDefinition(
        name="event",
        title="Generate Event",
        description="Generate a domain event class",
        contributor="events",
        generator_path="lexigram.events.cli.generators.event_generator:EventGenerator",
        default_output_dir="src/events",
        category="events",
    ),
    GeneratorDefinition(
        name="command",
        title="Generate Command",
        description="Generate a CQRS command handler",
        contributor="events",
        generator_path="lexigram.events.cli.generators.command_handler:CommandHandlerGenerator",
        default_output_dir="src/commands",
        category="events",
    ),
    GeneratorDefinition(
        name="query",
        title="Generate Query",
        description="Generate a CQRS query handler",
        contributor="events",
        generator_path="lexigram.events.cli.generators.query_handler:QueryHandlerGenerator",
        default_output_dir="src/queries",
        category="events",
    ),
)


class EventsCliContributor:
    """CLI contributor for the lexigram-events package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "events"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for events."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list[CommandContribution]:
        """Return the contributed `events` command group."""
        return [
            CommandContribution(
                name="events",
                help="Event schema and bus management commands",
                app_factory_path="lexigram.events.cli.commands:create_events_app",
                contributor="events",
                category="events",
                requires_app_context=False,
            ),
        ]

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return event bus health check."""
        return [
            HealthCheckContribution(
                name="event_bus_status",
                description="Verify event bus and store are operational",
                check_path="lexigram.events.cli.checks:check_event_bus",
                contributor="events",
                category="events",
                timeout=5.0,
            ),
        ]

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return event store configuration doctor checks."""
        return [
            DoctorCheckContribution(
                name="event_store_configured",
                description="Check event store backend is configured",
                check_path="lexigram.events.cli.doctor:check_event_store",
                contributor="events",
                category="events",
            ),
        ]

    def get_shell_context(self) -> list[ShellContextContribution]:
        """Return event bus shell context."""
        return [
            ShellContextContribution(
                name="events",
                description="Event bus for publishing/subscribing in shell",
                factory_path="lexigram.events.cli.shell:provide_event_bus",
                contributor="events",
            ),
        ]

    def get_hooks(self) -> list:
        """Return no hook contributions."""
        return []

    def get_schema_setup(self) -> list[SchemaSetupContribution]:
        """Return schema setup contributions for events."""
        return [
            SchemaSetupContribution(
                name="events.saga_records",
                description="Saga orchestration state storage",
                setup_fn_path="lexigram.events.cli.schema_setup:ensure_saga_records",
                contributor=self.contributor_id,
            ),
        ]


__all__ = ["EventsCliContributor"]
