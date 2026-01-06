"""lexigram-notification — SMS, push, email, and user inbox with Named DI multi-backend support."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.notification.errors import NotificationError
from lexigram.contracts.notification.inbox import InboxMessage, InboxStoreProtocol
from lexigram.contracts.notification.protocols import (
    PushChannelProtocol,
    SMSChannelProtocol,
)
from lexigram.contracts.notification.types import PushMessage, SMSMessage
from lexigram.notification.backends.push import WebPushChannel
from lexigram.notification.config import (
    APNsDriverConfig,
    FCMDriverConfig,
    InboxConfig,
    MailerConfig,
    NamedMailerConfig,
    NamedPushConfig,
    NamedSMSConfig,
    NotificationConfig,
    SendGridDriverConfig,
    SMTPDriverConfig,
    TwilioDriverConfig,
    WebPushDriverConfig,
)
from lexigram.notification.constants import __version__
from lexigram.notification.events import (
    EmailBouncedEvent,
    EmailSentEvent,
    InboxMessageCreatedEvent,
    InboxMessageReadEvent,
    NotificationFailedEvent,
    NotificationSentEvent,
)
from lexigram.notification.exceptions import (
    APNsNotificationError,
    FCMNotificationError,
    InboxError,
    InboxMessageNotFoundError,
    InboxPermissionError,
    SendGridMailerError,
    SMTPMailerError,
    TwilioNotificationError,
    WebPushNotificationError,
)
from lexigram.notification.hooks import (
    NotificationFailedHook,
    NotificationSentHook,
)
from lexigram.notification.inbox.database import DatabaseInboxStore
from lexigram.notification.inbox.memory import InMemoryInboxStore
from lexigram.notification.inbox.service import InboxService
from lexigram.notification.mailer.mailable import Mailable
from lexigram.notification.mailer.retrying_mailer import RetryingMailer
from lexigram.notification.mailer.sendgrid_mailer import SendGridMailer
from lexigram.notification.mailer.smtp_mailer import SMTPMailer
from lexigram.notification.module import NotificationModule
from lexigram.notification.protocols import (
    InboxStoreProtocol,
    MailerProtocol,
    PushChannelProtocol,
    SMSChannelProtocol,
)

__all__ = [
    "APNsDriverConfig",
    "APNsNotificationError",
    "DatabaseInboxStore",
    "EmailBouncedEvent",
    "EmailSentEvent",
    "FCMDriverConfig",
    "FCMNotificationError",
    "InMemoryInboxStore",
    "InboxConfig",
    "InboxError",
    "InboxMessage",
    "InboxMessageCreatedEvent",
    "InboxMessageNotFoundError",
    "InboxMessageReadEvent",
    "InboxPermissionError",
    "InboxService",
    "InboxStoreProtocol",
    "Mailable",
    "MailerConfig",
    "MailerProtocol",
    "NamedMailerConfig",
    "NamedPushConfig",
    "NamedSMSConfig",
    "NotificationConfig",
    "NotificationError",
    "NotificationFailedEvent",
    "NotificationFailedHook",
    "NotificationModule",
    "NotificationSentEvent",
    "NotificationSentHook",
    "PushChannelProtocol",
    "PushMessage",
    "RetryingMailer",
    "SMSChannelProtocol",
    "SMSMessage",
    "SMTPDriverConfig",
    "SMTPMailer",
    "SMTPMailerError",
    "SendGridMailer",
    "SendGridMailerError",
    "TwilioDriverConfig",
    "TwilioNotificationError",
    "WebPushChannel",
    "WebPushDriverConfig",
    "WebPushNotificationError",
    "__version__",
]
