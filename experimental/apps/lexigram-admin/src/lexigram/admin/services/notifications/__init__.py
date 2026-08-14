"""Admin notification services package."""

from __future__ import annotations

from lexigram.admin.services.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationRecipient,
    NotificationResult,
    NotificationType,
)
from lexigram.admin.services.notifications.sender import EmailSender
from lexigram.admin.services.notifications.service import AdminNotificationService
from lexigram.admin.services.notifications.templates import (
    ADMIN_EMAIL_BASE,
    EMAIL_TEMPLATES,
    TemplateRenderer,
)

__all__ = [
    # Templates
    "ADMIN_EMAIL_BASE",
    "EMAIL_TEMPLATES",
    # Service
    "AdminNotificationService",
    "EmailSender",
    "Notification",
    "NotificationChannel",
    "NotificationRecipient",
    "NotificationResult",
    # Models
    "NotificationType",
    "TemplateRenderer",
]
