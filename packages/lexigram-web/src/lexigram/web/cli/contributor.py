"""Web CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import DoctorCheckContribution
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="controller",
        title="Generate Controller",
        description="Generate a web controller with route handlers",
        contributor="web",
        generator_path="lexigram.web.cli.generators.controller:ControllerGenerator",
        default_output_dir="src/controllers",
        category="web",
    ),
    GeneratorDefinition(
        name="resource",
        title="Generate Resource",
        description="Generate a RESTful resource with CRUD endpoints",
        contributor="web",
        generator_path="lexigram.web.cli.generators.resource:ResourceGenerator",
        default_output_dir="src",
        category="web",
    ),
    GeneratorDefinition(
        name="middleware",
        title="Generate Middleware",
        description="Generate a web middleware component",
        contributor="web",
        generator_path="lexigram.web.cli.generators.middleware:MiddlewareGenerator",
        default_output_dir="src/middleware",
        category="web",
    ),
    GeneratorDefinition(
        name="graphql",
        title="Generate GraphQL",
        description="Generate a GraphQL schema and resolvers",
        contributor="web",
        generator_path="lexigram.web.cli.generators.graphql:GraphQLGenerator",
        default_output_dir="src/graphql",
        category="web",
    ),
    GeneratorDefinition(
        name="webhook",
        title="Generate Webhook",
        description="Generate a webhook handler",
        contributor="web",
        generator_path="lexigram.web.cli.generators.webhook:WebhookGenerator",
        default_output_dir="src/webhooks",
        category="web",
    ),
    GeneratorDefinition(
        name="websocket",
        title="Generate WebSocket",
        description="Generate a WebSocket handler",
        contributor="web",
        generator_path="lexigram.web.cli.generators.websocket:WebSocketHandlerGenerator",
        default_output_dir="src/websocket",
        category="web",
    ),
)


class WebCliContributor:
    """CLI contributor for the lexigram-web package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "web"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for web."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list:
        """Return no command contributions — web does not add command groups."""
        return []

    def get_health_checks(self) -> list:
        """Return no health check contributions."""
        return []

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return doctor checks for web route validation."""
        return [
            DoctorCheckContribution(
                name="web_routes_valid",
                description="Validate registered routes have valid controllers",
                check_path="lexigram.web.cli.checks:check_routes_valid",
                contributor="web",
                category="web",
            ),
        ]

    def get_shell_context(self) -> list:
        """Return no shell context contributions."""
        return []

    def get_hooks(self) -> list:
        """Return no hook contributions."""
        return []


__all__ = ["WebCliContributor"]
