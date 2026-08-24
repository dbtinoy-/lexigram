"""Notification configuration facade.

Re-exports every public name so that
``from lexigram.notification.config import X`` continues to work unchanged.
"""

from lexigram.notification.config.inbox import InboxConfig as InboxConfig
from lexigram.notification.config.mailer import (
    MailerConfig as MailerConfig,
)
from lexigram.notification.config.mailer import (
    NamedMailerConfig as NamedMailerConfig,
)
from lexigram.notification.config.mailer import (
    SendGridDriverConfig as SendGridDriverConfig,
)
from lexigram.notification.config.mailer import (
    SMTPDriverConfig as SMTPDriverConfig,
)
from lexigram.notification.config.push import (
    APNsDriverConfig as APNsDriverConfig,
)
from lexigram.notification.config.push import (
    FCMDriverConfig as FCMDriverConfig,
)
from lexigram.notification.config.push import (
    NamedPushConfig as NamedPushConfig,
)
from lexigram.notification.config.push import (
    WebPushDriverConfig as WebPushDriverConfig,
)
from lexigram.notification.config.sms import (
    NamedSMSConfig as NamedSMSConfig,
)
from lexigram.notification.config.sms import (
    TwilioDriverConfig as TwilioDriverConfig,
)
from lexigram.notification.config.top_level import (
    NotificationConfig as NotificationConfig,
)

__all__ = [
    "APNsDriverConfig",
    "FCMDriverConfig",
    "InboxConfig",
    "MailerConfig",
    "NamedMailerConfig",
    "NamedPushConfig",
    "NamedSMSConfig",
    "NotificationConfig",
    "SMTPDriverConfig",
    "SendGridDriverConfig",
    "TwilioDriverConfig",
    "WebPushDriverConfig",
]
