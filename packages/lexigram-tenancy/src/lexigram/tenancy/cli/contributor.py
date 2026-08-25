"""Tenancy CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    DoctorCheckContribution,
    ShellContextContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

# (name, description, generator_path, output_dir) — titles derive via make()
_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "tenant_resolver",
        "Generate a custom tenant resolver strategy",
        "lexigram.tenancy.cli.generators.resolver:TenantResolverGenerator",
        "src/tenancy",
    ),
)

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = tuple(
    GeneratorDefinition.make(
        name,
        description=description,
        generator_path=generator_path,
        output_dir=output_dir,
        contributor="tenancy",
        category="tenancy",
    )
    for name, description, generator_path, output_dir in _SPECS
)


class TenancyCliContributor:
    """CLI contributor for the lexigram-tenancy package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "tenancy"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for tenancy."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list[CommandContribution]:
        """Return the contributed `tenancy` command group."""
        return [
            CommandContribution(
                name="tenancy",
                help="Multi-tenant management commands",
                app_factory_path="lexigram.tenancy.cli.commands:create_tenancy_app",
                contributor="tenancy",
                category="tenancy",
                requires_app_context=True,
            ),
        ]

    def get_health_checks(self) -> list[object]:
        """Return no health check contributions."""
        return []

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return tenancy configuration doctor checks."""
        return [
            DoctorCheckContribution(
                name="tenancy_config_valid",
                description="Validate tenancy section in application.yaml",
                check_path="lexigram.tenancy.cli.doctor:check_tenancy_config",
                contributor="tenancy",
                category="tenancy",
            ),
            DoctorCheckContribution(
                name="isolation_strategy_valid",
                description="Check isolation strategy is properly configured",
                check_path="lexigram.tenancy.cli.doctor:check_isolation_strategy",
                contributor="tenancy",
                category="tenancy",
            ),
        ]

    def get_shell_context(self) -> list[ShellContextContribution]:
        """Return tenant lifecycle service shell context."""
        return [
            ShellContextContribution(
                name="tenancy",
                description="TenantLifecycleService for interactive tenant management",
                factory_path="lexigram.tenancy.cli.shell:provide_tenant_service",
                contributor="tenancy",
            ),
        ]

    def get_hooks(self) -> list[object]:
        """Return no hook contributions."""
        return []


__all__ = ["TenancyCliContributor"]
