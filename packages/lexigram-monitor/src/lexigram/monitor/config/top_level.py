"""Top-level monitor configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from lexigram.config import BaseConfig
from lexigram.contracts.core.config import ConfigIssue, Environment
from lexigram.monitor import constants as monitor_const
from lexigram.monitor.config.enums import BackendType
from lexigram.monitor.config.exporters import (
    OpenTelemetryConfig,
    PrometheusConfig,
    SLOConfig,
)
from lexigram.monitor.config.health import HealthCheckConfig, LoggingConfig
from lexigram.monitor.config.metrics import MetricsConfig
from lexigram.monitor.config.tracing import TracingConfig
from lexigram.validation import ConfigDict, Field, SecretStr, field_validator


@dataclass(init=False)
class ErrorTrackingConfig(BaseConfig):
    """External error tracking configuration (Sentry).

    When ``dsn`` is unset (the default), error tracking is a no-op so the
    integration adds no overhead or network traffic unless explicitly
    enabled (env: ``LEX_MONITOR__ERROR_TRACKING__DSN``).

    Attributes:
        dsn: Sentry DSN. Unset/empty disables error tracking entirely.
        environment: Environment tag attached to captured events.
        traces_sample_rate: Sampling rate for traces (0.0 to 1.0).
        send_default_pii: Whether to send default PII fields.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    dsn: SecretStr | None = Field(
        None,
        description="Sentry DSN; error tracking is a no-op when unset",
    )

    @field_validator("dsn", mode="before")
    @classmethod
    def _coerce_dsn(cls, value: Any) -> Any:
        """Accept plain strings from env/YAML; store as SecretStr."""
        if value is None or isinstance(value, SecretStr):
            return value
        return SecretStr(str(value))

    environment: Any = Field(
        None,
        description="Environment tag for captured events",
    )
    traces_sample_rate: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Traces sample rate (0.0 to 1.0)",
    )
    send_default_pii: bool = Field(
        False,
        description="Send default PII fields to the error tracker",
    )


@dataclass(init=False)
class MonitorConfig(BaseConfig):
    """Hierarchical root configuration for Lexigram Monitor.

    Attributes:
        enabled: Whether monitoring is enabled
        name: Configuration name (default: "monitor")
        backend_type: Monitoring backend type
        metrics: Metrics configuration
        tracing: Tracing configuration
        health: Health check configuration
        logging: Logging configuration
        slo: SLO evaluation configuration
        error_tracking: External error tracking configuration
        opentelemetry: OpenTelemetry configuration
        prometheus: Prometheus configuration
        environment: Environment name
        debug: Debug mode
    """

    config_section: ClassVar[str] = "monitor"

    model_config: ClassVar[ConfigDict] = ConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix=monitor_const.ENV_PREFIX,
        env_nested_delimiter=monitor_const.ENV_NESTED_DELIMITER,
        extra="ignore",
    )

    enabled: bool = Field(True, description="Enable monitoring")
    name: str = Field(monitor_const.DEFAULT_SERVICE_NAME, description="Provider name")
    backend_type: BackendType = Field(
        BackendType.MEMORY,
        description="Monitoring backend type",
    )
    metrics: MetricsConfig = Field(
        default_factory=MetricsConfig,
        description="Metrics configuration",
    )
    tracing: TracingConfig = Field(
        default_factory=TracingConfig,
        description="Tracing configuration",
    )
    health: HealthCheckConfig = Field(
        default_factory=HealthCheckConfig,
        description="Health check configuration",
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration",
    )
    slo: SLOConfig = Field(
        default_factory=SLOConfig,
        description="SLO evaluation configuration",
    )
    error_tracking: ErrorTrackingConfig = Field(
        default_factory=ErrorTrackingConfig,
        description="External error tracking configuration",
    )
    opentelemetry: OpenTelemetryConfig = Field(
        default_factory=OpenTelemetryConfig,
        description="OpenTelemetry configuration",
    )
    prometheus: PrometheusConfig = Field(
        default_factory=PrometheusConfig,
        description="Prometheus configuration",
    )
    environment: Environment = Field(
        Environment.DEVELOPMENT, description="Deployment environment"
    )
    env: str | None = Field(
        None, description="Environment (development/staging/production)"
    )
    debug: bool = Field(False, description="Enable debug mode")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return (self.env or self.environment) == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        env_val = self.env or self.environment
        return env_val in ("development", "dev")

    @property
    def is_test(self) -> bool:
        """Check if running in test environment."""
        env_val = self.env or self.environment
        return env_val in ("test", "testing")

    def validate_for_environment(
        self, env: Environment | None = None
    ) -> list[ConfigIssue]:
        """Validate monitoring configuration for the given environment.

        Args:
            env: Target environment; resolved from ``LEX_ENV`` when ``None``.

        Returns:
            List of :class:`~lexigram.contracts.core.config.ConfigIssue` instances.
        """
        resolved = env or Environment.from_env()
        issues: list[ConfigIssue] = []
        if resolved == Environment.PRODUCTION and not self.tracing.enabled:
            issues.append(
                ConfigIssue(
                    field="tracing.enabled",
                    message="Distributed tracing is disabled in production.",
                    severity="warning",
                    suggestion=(
                        "Set LEX_MONITOR__TRACING__ENABLED=true and configure "
                        "an OTLP endpoint for production observability."
                    ),
                )
            )
        return issues

    def get_backend_config(self) -> OpenTelemetryConfig | PrometheusConfig | None:
        """Get the configuration for the selected backend.

        Returns:
            Backend-specific configuration or None for memory backend.
        """
        if self.backend_type == BackendType.OPENTELEMETRY:
            return self.opentelemetry
        if self.backend_type == BackendType.PROMETHEUS:
            return self.prometheus
        return None

    def make_exporter(self) -> Any | None:
        """Construct an optional metrics exporter appropriate for the backend.

        Returns:
            MetricsExporter instance or None if no exporter is available.
        """
        if self.backend_type == BackendType.PROMETHEUS:
            try:
                from lexigram.monitor.backends.exporters import (
                    PrometheusMetricsExporter,
                )

                return PrometheusMetricsExporter()
            except (ImportError, RuntimeError, TypeError):
                return None
        # OTLP and memory backends do not provide a dedicated MetricsExporter
        return None


__all__ = [
    "ErrorTrackingConfig",
    "MonitorConfig",
]
