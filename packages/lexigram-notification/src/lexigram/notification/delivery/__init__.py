"""Notification delivery retry queue module."""

from __future__ import annotations

from lexigram.notification.delivery.exceptions import PermanentDeliveryFailure
from lexigram.notification.delivery.retry import RetryingMailer

__all__ = ["PermanentDeliveryFailure", "RetryingMailer"]
