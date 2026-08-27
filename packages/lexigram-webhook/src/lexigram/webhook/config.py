"""Configuration for the webhook management subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config.base import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.validation import ConfigDict, Field
from lexigram.webhook import constants as const


@dataclass(init=False)
class WebhookConfig(BaseConfig):
    """Configuration for the webhook management subsystem.

    Attributes:
        store_backend: Persistence backend. "sql" requires lexigram-webhook[sql].
        retry_max_attempts: Maximum delivery attempts before dead-letter.
        retry_base_delay: Initial retry delay in seconds.
        retry_max_delay: Maximum retry delay ceiling in seconds.
        retry_backoff_factor: Exponential backoff multiplier.
        secret_length: Secret length in bytes (hex-encoded output is 2x).
        secret_rotation_grace_hours: Hours both old and new secrets are accepted.
        delivery_timeout_seconds: HTTP request timeout per delivery attempt.
        disable_after_consecutive_failures: Auto-disable threshold.
        failure_window_hours: Window for counting consecutive failures.
        signature_algorithm: HMAC algorithm name.
        enable_admin: Whether to register the admin contributor.
        delivery_log_retention_days: Days to retain delivery log (0 = indefinite).
        signature_header: HTTP header for the HMAC signature.
        event_type_header: HTTP header for the event type.
        event_id_header: HTTP header for the event ID.
        timestamp_header: HTTP header for the delivery timestamp.
    """

    config_section: ClassVar[str] = "webhook"

    name: str = "webhook"
    enabled: bool = True
    env: Environment | None = Field(None, description="Deployment environment")

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    store_backend: str = Field(
        const.DEFAULT_STORE_BACKEND,
        description="Persistence backend ('sql' requires lexigram-webhook[sql])",
    )
    allow_private_urls: bool = Field(
        False,
        description=(
            "Allow registering and delivering webhooks to private, loopback, "
            "or link-local URLs (local development only). Defaults to deny."
        ),
    )
    retry_max_attempts: int = Field(
        const.DEFAULT_RETRY_MAX_ATTEMPTS,
        description="Maximum delivery attempts before dead-letter",
    )
    retry_base_delay: float = Field(
        const.DEFAULT_RETRY_BASE_DELAY,
        description="Initial retry delay in seconds",
    )
    retry_max_delay: float = Field(
        const.DEFAULT_RETRY_MAX_DELAY,
        description="Maximum retry delay ceiling in seconds",
    )
    retry_backoff_factor: float = Field(
        const.DEFAULT_RETRY_BACKOFF_FACTOR,
        description="Exponential backoff multiplier",
    )
    secret_length: int = Field(
        const.DEFAULT_SECRET_LENGTH,
        description="Secret length in bytes (hex-encoded output is 2x)",
    )
    secret_rotation_grace_hours: int = Field(
        const.DEFAULT_SECRET_ROTATION_GRACE_HOURS,
        description="Hours both old and new secrets are accepted",
    )
    delivery_timeout_seconds: float = Field(
        const.DEFAULT_DELIVERY_TIMEOUT_SECONDS,
        description="HTTP request timeout per delivery attempt",
    )
    disable_after_consecutive_failures: int = Field(
        const.DEFAULT_DISABLE_AFTER_CONSECUTIVE_FAILURES,
        description="Auto-disable threshold",
    )
    failure_window_hours: int = Field(
        const.DEFAULT_FAILURE_WINDOW_HOURS,
        description="Window for counting consecutive failures",
    )
    signature_algorithm: str = Field(
        const.DEFAULT_SIGNATURE_ALGORITHM,
        description="HMAC algorithm name",
    )
    enable_admin: bool = Field(
        True,
        description="Whether to register the admin contributor",
    )
    delivery_log_retention_days: int = Field(
        const.DEFAULT_DELIVERY_LOG_RETENTION_DAYS,
        description="Days to retain delivery log (0 = indefinite)",
    )
    signature_header: str = Field(
        const.DEFAULT_SIGNATURE_HEADER,
        description="HTTP header for the HMAC signature",
    )
    event_type_header: str = Field(
        const.DEFAULT_EVENT_TYPE_HEADER,
        description="HTTP header for the event type",
    )
    event_id_header: str = Field(
        const.DEFAULT_EVENT_ID_HEADER,
        description="HTTP header for the event ID",
    )
    timestamp_header: str = Field(
        const.DEFAULT_TIMESTAMP_HEADER,
        description="HTTP header for the delivery timestamp",
    )


__all__ = ["WebhookConfig"]
