"""Mailer submodule — email delivery backends, mailable base, and IoC module."""

from __future__ import annotations

from lexigram.notification.mailer.mailable import Mailable
from lexigram.notification.mailer.module import MailerModule
from lexigram.notification.mailer.retrying_mailer import RetryingMailer
from lexigram.notification.mailer.sendgrid_mailer import SendGridMailer
from lexigram.notification.mailer.smtp_mailer import SMTPMailer

__all__ = [
    "Mailable",
    "MailerModule",
    "RetryingMailer",
    "SMTPMailer",
    "SendGridMailer",
]
