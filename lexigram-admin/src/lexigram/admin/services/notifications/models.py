"""Notification data models and types for admin notifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class NotificationType(StrEnum):
    """Types of admin notifications."""

    # User events
    USER_CREATED = "user_created"
    USER_INVITED = "user_invited"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"
    PASSWORD_RESET = "password_reset"  # noqa: S105  # event type name, not a credential
    EMAIL_VERIFICATION = "email_verification"
    EMAIL_OTP = "email_otp"
    PASSWORD_CHANGED = "password_changed"  # noqa: S105  # event type name, not a credential

    # Bulk operations
    BULK_STARTED = "bulk_started"
    BULK_PROGRESS = "bulk_progress"
    BULK_COMPLETED = "bulk_completed"
    BULK_FAILED = "bulk_failed"

    # System events
    SYSTEM_ALERT = "system_alert"
    SYSTEM_WARNING = "system_warning"
    SYSTEM_ERROR = "system_error"

    # Export/Import
    EXPORT_READY = "export_ready"
    IMPORT_COMPLETED = "import_completed"
    IMPORT_FAILED = "import_failed"


class NotificationChannel(StrEnum):
    """Notification delivery channels."""

    EMAIL = "email"
    IN_APP = "in_app"
    PUSH = "push"


@dataclass
class NotificationRecipient:
    """Notification recipient."""

    email: str
    name: str | None = None
    user_id: Any = None
    preferences: dict[str, bool] = field(default_factory=dict)

    def can_receive(self, notification_type: NotificationType) -> bool:
        """Check if recipient can receive notification type."""
        key = f"notify_{notification_type.value}"
        return self.preferences.get(key, True)


@dataclass
class Notification:
    """Admin notification."""

    type: NotificationType
    subject: str
    body: str
    recipients: list[NotificationRecipient]
    channels: list[NotificationChannel] = field(
        default_factory=lambda: [NotificationChannel.EMAIL],
    )

    # Optional fields
    data: dict[str, Any] = field(default_factory=dict)
    html_body: str | None = None
    priority: str = "normal"
    scheduled_at: datetime | None = None

    # Tracking
    id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class NotificationResult:
    """Payload of a completed notification delivery.

    Always carried inside ``Ok[NotificationResult, NotificationError]``.
    Per-recipient failures are tracked in ``errors`` and ``recipients_failed``;
    a non-zero ``recipients_failed`` does NOT mean the overall operation failed —
    only an ``Err`` return (when every recipient failed) does.
    """

    notification_id: str | None = None
    recipients_sent: int = 0
    recipients_failed: int = 0
    errors: list[str] = field(default_factory=list)


__all__ = [
    "Notification",
    "NotificationChannel",
    "NotificationRecipient",
    "NotificationResult",
    "NotificationType",
]
