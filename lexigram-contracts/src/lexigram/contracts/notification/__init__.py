# lexigram-contracts/src/lexigram/contracts/notification/__init__.py
"""Notification protocols, types, and errors."""

from __future__ import annotations

from lexigram.contracts.notification.delivery import (
    DeliveryStatus,
    DeliveryStoreProtocol,
)
from lexigram.contracts.notification.errors import NotificationError
from lexigram.contracts.notification.inbox import InboxMessage, InboxStoreProtocol
from lexigram.contracts.notification.protocols import (
    PushChannelProtocol,
    SMSChannelProtocol,
)
from lexigram.contracts.notification.types import PushMessage, SMSMessage
from lexigram.contracts.notification.web_push import WebPushKeys, WebPushSubscription

__all__ = [
    "DeliveryStatus",
    "DeliveryStoreProtocol",
    "InboxMessage",
    "InboxStoreProtocol",
    "NotificationError",
    "PushChannelProtocol",
    "PushMessage",
    "SMSChannelProtocol",
    "SMSMessage",
    "WebPushKeys",
    "WebPushSubscription",
]
