"""Observability, storage, and notification configurations."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False)
class AdminObservabilityConfig(DomainModel):
    metrics_enabled: bool = Field(default=True)
    high_cardinality_labels_enabled: bool = Field(default=False)


@dataclass(init=False)
class AdminStorageConfig(DomainModel):
    """Configuration for admin file storage service."""

    base_path: str = Field(
        default="uploads", description="Base path for uploaded files"
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum allowed file size in bytes (default 10 MB)",
    )
    allowed_content_types: list[str] = Field(
        default_factory=lambda: [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "application/pdf",
            "text/plain",
            "text/csv",
        ],
        description="Allowed MIME content types for uploads",
    )
    presigned_url_expiry: int = Field(
        default=3600,
        description="Default expiry for presigned URLs in seconds",
    )


@dataclass(init=False)
class AdminNotificationConfig(DomainModel):
    """Configuration for admin notification service.

    Controls email notification behaviour, delivery channels, and
    retry settings.
    """

    email_from: str = Field(
        default="admin@localhost", description="Sender email address"
    )
    email_from_name: str = Field(
        default="Admin Panel", description="Sender display name"
    )
    default_channel: str = Field(
        default="email", description="Default delivery channel"
    )
    max_retries: int = Field(default=3, description="Maximum delivery retry attempts")
    retry_delay_seconds: int = Field(default=60, description="Seconds between retries")
    enabled: bool = Field(default=True, description="Enable notification sending")
