"""lexigram-notification DI module."""

from __future__ import annotations

from lexigram.notification.di.inbox_provider import InboxProvider
from lexigram.notification.di.mailer_provider import MailerProvider
from lexigram.notification.di.provider import NotificationProvider

__all__ = ["InboxProvider", "MailerProvider", "NotificationProvider"]
