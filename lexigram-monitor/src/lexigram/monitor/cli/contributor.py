"""Monitor CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    DoctorCheckContribution,
    HealthCheckContribution,
    HookContribution,
    ShellContextContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="metric",
        title="Generate Metric",
        description="Generate a custom metric definition with backend registration",
        contributor="monitor",
        generator_path="lexigram.monitor.cli.generators.metric:MetricGenerator",
        default_output_dir="src/metrics",
        category="monitoring",
    ),
)


class MonitorCliContributor:
    """CLI contributor for the lexigram-monitor package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "monitor"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for monitor."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list[CommandContribution]:
        """Return the contributed `monitor` command group."""
        return [
            CommandContribution(
                name="monitor",
                help="Observability and monitoring commands",
                app_factory_path="lexigram.monitor.cli.commands:create_monitor_app",
                contributor="monitor",
                category="monitoring",
                requires_app_context=True,
            ),
        ]

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return monitoring backend health checks."""
        return [
            HealthCheckContribution(
                name="metrics_backend",
                description="Verify metrics backend (Prometheus/OTLP) connectivity",
                check_path="lexigram.monitor.cli.checks:check_metrics_backend",
                contributor="monitor",
                category="monitoring",
                timeout=10.0,
            ),
            HealthCheckContribution(
                name="tracing_backend",
                description="Verify tracing backend connectivity",
                check_path="lexigram.monitor.cli.checks:check_tracing_backend",
                contributor="monitor",
                category="monitoring",
                timeout=10.0,
            ),
        ]

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return monitoring configuration doctor checks."""
        return [
            DoctorCheckContribution(
                name="monitor_config_valid",
                description="Validate monitor section in application.yaml",
                check_path="lexigram.monitor.cli.doctor:check_monitor_config",
                contributor="monitor",
                category="monitoring",
            ),
            DoctorCheckContribution(
                name="otel_endpoint_reachable",
                description="Check OTEL_EXPORTER_OTLP_ENDPOINT is reachable",
                check_path="lexigram.monitor.cli.doctor:check_otel_endpoint",
                contributor="monitor",
                category="monitoring",
            ),
        ]

    def get_shell_context(self) -> list[ShellContextContribution]:
        """Return metrics shell context."""
        return [
            ShellContextContribution(
                name="metrics",
                description="Metrics backend for interactive metric queries",
                factory_path="lexigram.monitor.cli.shell:provide_metrics",
                contributor="monitor",
            ),
        ]

    def get_hooks(self) -> list[HookContribution]:
        """Return command metric recording hook."""
        return [
            HookContribution(
                event="post_command",
                handler_path="lexigram.monitor.cli.hooks:record_command_metric",
                contributor="monitor",
                priority=100,
            ),
        ]


__all__ = ["MonitorCliContributor"]
