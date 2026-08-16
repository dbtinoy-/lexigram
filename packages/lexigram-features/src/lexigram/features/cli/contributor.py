"""Features CLI contributor definitions."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    DoctorCheckContribution,
    HealthCheckContribution,
    ShellContextContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="feature_flag",
        title="Generate Feature Flag",
        description="Generate a feature flag definition",
        contributor="features",
        generator_path="lexigram.features.cli.generators.flag:FeatureFlagGenerator",
        default_output_dir="src/features",
        category="features",
    ),
)


class FeaturesCliContributor:
    """CLI contributor for the lexigram-features package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "features"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for features."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list[CommandContribution]:
        """Return the contributed `features` command group."""
        return [
            CommandContribution(
                name="features",
                help="Feature flag management commands",
                app_factory_path="lexigram.features.cli.commands:create_features_app",
                contributor="features",
                category="features",
                requires_app_context=True,
            ),
        ]

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return feature flag manager health checks."""
        return [
            HealthCheckContribution(
                name="flag_manager_status",
                description="Check feature flag manager is operational",
                check_path="lexigram.features.cli.checks:check_flag_manager",
                contributor="features",
                category="features",
                timeout=5.0,
            ),
        ]

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return features configuration doctor checks."""
        return [
            DoctorCheckContribution(
                name="features_config_valid",
                description="Validate features section in application.yaml",
                check_path="lexigram.features.cli.doctor:check_features_config",
                contributor="features",
                category="features",
            ),
        ]

    def get_shell_context(self) -> list[ShellContextContribution]:
        """Return flag manager shell context."""
        return [
            ShellContextContribution(
                name="flags",
                description="FlagManager for interactive feature flag management",
                factory_path="lexigram.features.cli.shell:provide_flag_manager",
                contributor="features",
            ),
        ]

    def get_hooks(self) -> list[Any]:
        """Return no hook contributions."""
        return []


__all__ = ["FeaturesCliContributor"]
