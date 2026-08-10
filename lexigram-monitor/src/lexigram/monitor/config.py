"""Configuration models for Lexigram Monitor.

This module provides Pydantic models for configuring monitoring,
metrics, tracing, and health checks.

Example:
    from lexigram.monitor.config import MonitorConfig

    # From YAML
    config = MonitorConfig.from_yaml("application.yaml")

    # From environment
    config = MonitorConfig()  # reads LEX_MONITOR__* env vars
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar

from lexigram.config import BaseConfig
from lexigram.contracts.core.config import ConfigIssue, Environment
from lexigram.monitor import constants as monitor_const
from lexigram.validation import ConfigDict, Field, field_validator


class BackendType(StrEnum):
    """Supported monitoring backend types."""

    OPENTELEMETRY = "opentelemetry"
    PROMETHEUS = "prometheus"
    MEMORY = "memory"


class SamplerType(StrEnum):
    """Supported tracing sampler types."""

    ALWAYS_ON = "always_on"
    ALWAYS_OFF = "always_off"
    PROBABILITY = "probability"
    RATE_LIMITING = "rate_limiting"
    PARENT_BASED = "parent_based"


@dataclass(init=False)
class MetricsConfig(BaseConfig):
    """Configuration for metrics collection.

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    Attributes:
        enabled: Whether metrics collection is enabled.
        prefix: Prefix for all metric names.
        default_labels: Default labels to add to all metrics.
        histogram_buckets: Default bucket boundaries for histograms.
        collection_interval: Interval for periodic metrics collection (seconds).
    """

    enabled: bool = Field(True, description="Enable metrics collection")
    prefix: str = Field(
        monitor_const.METRIC_PREFIX, description="MetricProtocol name prefix"
    )
    default_labels: dict[str, str] = Field(
        default_factory=dict,
        description="Default labels for all metrics",
    )
    histogram_buckets: list[float] = Field(
        default_factory=lambda: list(monitor_const.DEFAULT_DURATION_BUCKETS),
        description="Default histogram bucket boundaries",
    )
    collection_interval: float = Field(
        60.0,
        ge=1.0,
        description="Metrics collection interval in seconds",
    )

    def make_metric_name(self, name: str) -> str:
        """Create a prefixed metric name.

        Args:
            name: The metric name.

        Returns:
            Prefixed metric name.
        """
        if self.prefix:
            return f"{self.prefix}_{name}"
        return name


@dataclass(init=False)
class TracingConfig(BaseConfig):
    """Configuration for distributed tracing.

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    Attributes:
        enabled: Whether tracing is enabled.
        service_name: Name of the service for traces.
        sampler_type: Type of sampling strategy.
        sample_rate: Sampling rate (0.0 to 1.0) for probability sampler.
        max_traces_per_second: Max traces/sec for rate limiting sampler.
        propagation_formats: Trace context propagation formats.
        max_attributes: Maximum attributes per span.
        max_events: Maximum events per span.
        max_links: Maximum links per span.
    """

    enabled: bool = Field(True, description="Enable tracing")
    service_name: str = Field(
        monitor_const.DEFAULT_SERVICE_NAME, description="Service name for traces"
    )
    sampler_type: SamplerType = Field(
        SamplerType.ALWAYS_ON,
        description="Tracing sampler type",
    )
    sample_rate: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Sample rate (0.0 to 1.0)",
    )
    max_traces_per_second: int = Field(
        100,
        ge=0,
        description="Max traces to sample per second",
    )
    propagation_formats: list[str] = Field(
        default_factory=lambda: ["tracecontext", "baggage"],
        description="Propagation format list",
    )
    max_attributes: int = Field(128, ge=1, description="Max attributes per span")
    max_events: int = Field(128, ge=1, description="Max events per span")
    max_links: int = Field(128, ge=1, description="Max links per span")
    max_spans: int = Field(
        monitor_const.DEFAULT_MAX_SPANS,
        ge=1,
        description="Max number of spans to keep in memory",
    )

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: float) -> float:
        """Validate sample rate is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("sample_rate must be between 0.0 and 1.0")
        return v


@dataclass(init=False)
class HealthCheckConfig(BaseConfig):
    """Configuration for health checks.

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    Attributes:
        enabled: Whether health checks are enabled.
        path: HTTP path for health endpoint.
        include_details: Include detailed component health in response.
        timeout: Timeout for health check operations (seconds).
        checks: List of health check names to include.
    """

    enabled: bool = Field(True, description="Enable health checks")
    path: str = Field("/health", description="Health endpoint path")
    include_details: bool = Field(
        True,
        description="Include detailed health info in response",
    )
    timeout: float = Field(5.0, ge=0.1, description="Health check timeout in seconds")
    checks: list[str] = Field(
        default_factory=list,
        description="List of health check names to run",
    )
    interval: int = Field(
        monitor_const.DEFAULT_HEALTH_CHECK_INTERVAL,
        ge=1,
        description="Health check interval in seconds",
    )


@dataclass(init=False)
class LoggingConfig(BaseConfig):
    """Configuration for structured logging.

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    Attributes:
        enabled: Whether structured logging is enabled.
        level: Default log level.
        format: Log format (json, text).
        include_trace_context: Include trace context in logs.
        redact_fields: Fields to redact from logs.
    """

    enabled: bool = Field(True, description="Enable structured logging")
    level: str = Field("INFO", description="Default log level")
    format: str = Field("json", description="Log format (json, text)")
    include_trace_context: bool = Field(
        True,
        description="Include trace context in logs",
    )
    redact_fields: list[str] = Field(
        default_factory=lambda: [
            "password",
            "secret",
            "token",
            "api_key",
            "authorization",
        ],
        description="Fields to redact from logs",
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"level must be one of {valid_levels}")
        return v_upper


@dataclass(init=False)
class OTelExporterConfig(BaseConfig):
    """Configuration for OTel exporters."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    type: str = Field("console", description="Exporter type (console, jaeger, otlp)")
    endpoint: str | None = Field(None, description="Collector endpoint URL")
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Custom headers for OTLP",
    )


@dataclass(init=False)
class OpenTelemetryConfig(BaseConfig):
    """Configuration for OpenTelemetry backend.

    Attributes:
        endpoint: OTLP endpoint URL.
        headers: Headers to send with OTLP requests.
        insecure: Use insecure connection (no TLS).
        timeout: Export timeout in seconds.
        compression: Compression type (none, gzip).
        batch_size: Batch size for exports.
        export_interval: Export interval in seconds.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    endpoint: str | None = Field(None, description="OTLP endpoint URL")
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="OTLP request headers",
    )
    insecure: bool = Field(False, description="Use insecure connection")
    timeout: float = Field(30.0, ge=1.0, description="Export timeout seconds")
    compression: str = Field("none", description="Compression type (none, gzip)")
    batch_size: int = Field(512, ge=1, description="Export batch size")
    export_interval: float = Field(5.0, ge=0.1, description="Export interval seconds")
    tracing_exporters: list[OTelExporterConfig] = Field(
        default_factory=lambda: [OTelExporterConfig()],
        description="List of tracing exporters to build.",
    )
    metrics_exporters: list[OTelExporterConfig] = Field(
        default_factory=lambda: [OTelExporterConfig()],
        description="List of metrics exporters to build.",
    )

    @field_validator("compression")
    @classmethod
    def validate_compression(cls, v: str) -> str:
        """Validate compression type."""
        valid = {"none", "gzip"}
        if v.lower() not in valid:
            raise ValueError(f"compression must be one of {valid}")
        return v.lower()


@dataclass(init=False)
class PrometheusConfig(BaseConfig):
    """Configuration for Prometheus backend.

    Attributes:
        port: Port for metrics HTTP server.
        path: Path for metrics endpoint.
        enable_default_metrics: Enable default process metrics.
        pushgateway_url: Optional Pushgateway URL for push-based metrics.
        push_interval: Interval for pushing metrics to Pushgateway (seconds).
        store_in_db: Whether to persist metric observations to the database.
        metrics_table: Name of the metrics table to write samples to.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    port: int = Field(
        monitor_const.DEFAULT_PROMETHEUS_PORT,
        ge=1,
        le=65535,
        description="Metrics server port",
    )
    path: str = Field("/metrics", description="Metrics endpoint path")
    enable_default_metrics: bool = Field(
        True,
        description="Enable default process metrics",
    )
    pushgateway_url: str | None = Field(
        None,
        description="Pushgateway URL for push-based metrics",
    )
    push_interval: float = Field(
        10.0,
        ge=1.0,
        description="Push interval for Pushgateway",
    )
    # DB storage options
    store_in_db: bool = Field(False, description="Persist metrics observations to DB")
    metrics_table: str = Field(
        "metrics_samples",
        description="Table name for metrics samples",
    )


@dataclass(init=False)
class SLOConfig(BaseConfig):
    """Configuration for SLO evaluation and alerting.

    Attributes:
        enabled: Whether the SLO evaluation worker runs.
        evaluation_interval: Seconds between SLO evaluation cycles (default 60).
        suppression_window_seconds: Min seconds between duplicate alerts (default 300).
        alert_channels: List of alert channel names to dispatch SLO violations to.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(True, description="Enable periodic SLO evaluation worker")
    evaluation_interval: float = Field(
        60.0, ge=1.0, description="SLO evaluation interval in seconds"
    )
    suppression_window_seconds: int = Field(
        300, ge=0, description="Alert suppression window in seconds"
    )
    alert_channels: list[str] = Field(
        default_factory=list,
        description="Alert channel names for SLO violation dispatch",
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
        default_factory=lambda: ErrorTrackingConfig(),
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

    dsn: str | None = Field(
        None,
        description="Sentry DSN; error tracking is a no-op when unset",
    )
    environment: str | None = Field(
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


# Export all config classes
__all__ = [
    "BackendType",
    "ErrorTrackingConfig",
    "HealthCheckConfig",
    "LoggingConfig",
    "MetricsConfig",
    "MonitorConfig",
    "OTelExporterConfig",
    "OpenTelemetryConfig",
    "PrometheusConfig",
    "SLOConfig",
    "SamplerType",
    "TracingConfig",
]
