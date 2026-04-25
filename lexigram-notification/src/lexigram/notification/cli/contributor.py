"""Notification CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    DoctorCheckContribution,
    HealthCheckContribution,
    SchemaSetupContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="notification_template",
        title="Generate Notification Template",
        description="Generate a notification template",
        contributor="notification",
        generator_path="lexigram.notification.cli.generators.template:NotificationTemplateGenerator",
        default_output_dir="src/notifications",
        category="notification",
    ),
)


class NotificationCliContributor:
    """CLI contributor for the lexigram-notification package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "notification"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for notification."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list[CommandContribution]:
        """Return the contributed `notify` command group."""
        return [
            CommandContribution(
                name="notify",
                help="Notification channel management commands",
                app_factory_path="lexigram.notification.cli.commands:create_notify_app",
                contributor="notification",
                category="notification",
                requires_app_context=True,
            ),
        ]

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return notification channel health checks."""
        return [
            HealthCheckContribution(
                name="notification_channels",
                description="Check notification channels are reachable",
                check_path="lexigram.notification.cli.checks:check_notification_channels",
                contributor="notification",
                category="notification",
                timeout=15.0,
            ),
        ]

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return notification configuration doctor checks."""
        return [
            DoctorCheckContribution(
                name="smtp_configured",
                description="Check SMTP configuration is present",
                check_path="lexigram.notification.cli.doctor:check_smtp_config",
                contributor="notification",
                category="notification",
            ),
            DoctorCheckContribution(
                name="push_credentials_configured",
                description="Check push notification credentials are configured",
                check_path="lexigram.notification.cli.doctor:check_push_credentials",
                contributor="notification",
                category="notification",
            ),
        ]

    def get_shell_context(self) -> list:
        """Return no shell context contributions."""
        return []

    def get_hooks(self) -> list:
        """Return no hook contributions."""
        return []

    def get_schema_setup(self) -> list[SchemaSetupContribution]:
        """Return schema setup contributions for notification."""
        return [
            SchemaSetupContribution(
                name="notification.inbox_messages",
                description="In-app notification inbox storage",
                setup_fn_path="lexigram.notification.cli.schema_setup:ensure_inbox_messages",
                contributor=self.contributor_id,
            ),
        ]


__all__ = ["NotificationCliContributor"]
