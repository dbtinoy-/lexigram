"""Audit CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    DoctorCheckContribution,
    HealthCheckContribution,
    HookContribution,
    ShellContextContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition, GeneratorOption

_GENERATOR_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "audited",
        "Generate an audited async handler",
        "lexigram.audit.cli.generators.audited:AuditedHandlerGenerator",
        "src/audit",
    ),
)

_GENERATOR_OPTIONS: dict[str, tuple[GeneratorOption, ...]] = {
    "audited": (
        GeneratorOption(
            name="action",
            type_hint="str",
            description="Dot-notation action identifier (e.g. user.update)",
        ),
        GeneratorOption(
            name="resource_type",
            type_hint="str",
            description="Kind of affected resource (e.g. User)",
        ),
        GeneratorOption(
            name="severity",
            type_hint="str",
            description="Severity level recorded with the audit entry",
        ),
    ),
}

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = tuple(
    GeneratorDefinition.make(
        name,
        description=description,
        generator_path=generator_path,
        output_dir=output_dir,
        contributor="audit",
        category="security",
        options=_GENERATOR_OPTIONS.get(name, ()),
    )
    for name, description, generator_path, output_dir in _GENERATOR_SPECS
)


class AuditCliContributor:
    """CLI contributor for the lexigram-audit package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "audit"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return the contributed audit generator."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list[CommandContribution]:
        """Return the contributed `audit` command group."""
        return [
            CommandContribution(
                name="audit",
                help="Audit log query and management commands",
                app_factory_path="lexigram.audit.cli.commands:create_audit_app",
                contributor="audit",
                category="security",
                requires_app_context=True,
            ),
        ]

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return audit store health check."""
        return [
            HealthCheckContribution(
                name="audit_store_status",
                description="Verify audit log store is operational",
                check_path="lexigram.audit.cli.checks:check_audit_store",
                contributor="audit",
                category="security",
                timeout=10.0,
                critical=True,
            ),
        ]

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return audit HMAC key doctor check."""
        return [
            DoctorCheckContribution(
                name="audit_hmac_key_configured",
                description="Check AUDIT_HMAC_KEY env var is set",
                check_path="lexigram.audit.cli.doctor:check_hmac_key",
                contributor="audit",
                category="security",
            ),
        ]

    def get_shell_context(self) -> list[ShellContextContribution]:
        """Return audit logger shell context."""
        return [
            ShellContextContribution(
                name="audit",
                description="Audit logger for interactive log inspection",
                factory_path="lexigram.audit.cli.shell:provide_audit_logger",
                contributor="audit",
            ),
        ]

    def get_hooks(self) -> list[HookContribution]:
        """Return CLI command audit hook."""
        return [
            HookContribution(
                event="post_command",
                handler_path="lexigram.audit.cli.hooks:log_cli_command",
                contributor="audit",
                priority=80,
            ),
        ]


__all__ = ["AuditCliContributor"]
