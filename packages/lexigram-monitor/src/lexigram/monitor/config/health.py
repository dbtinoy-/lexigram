"""Health check and logging configuration."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.config import BaseConfig
from lexigram.monitor import constants as monitor_const
from lexigram.validation import Field, field_validator


@dataclass(init=False)
class HealthCheckConfig(BaseConfig):
    """Configuration for health checks.

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


__all__ = [
    "HealthCheckConfig",
    "LoggingConfig",
]
