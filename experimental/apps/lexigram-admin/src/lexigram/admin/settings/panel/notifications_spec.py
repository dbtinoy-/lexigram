"""Email & notification configuration specification (R39, doc 35)."""

from __future__ import annotations

from lexigram.admin.settings.panel.models import NotificationSettings
from lexigram.admin.settings.panel.nodes import EmailNode, PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["NotificationsSpec", "register_spec"]


class NotificationsSpec(PydanticConfigSpec):
    """Outbound email sender identity spec.

    Values are consumed by ``AdminNotificationService`` on a 30 s TTL
    (doc 35 §2.2), so panel saves apply without a restart.
    """

    namespace = "admin.notifications"
    label = "Email & Notifications"
    icon = "envelope"
    description = (
        "Sender identity for verification, password-reset, and "
        "notification emails. Delivery status lives on the Email page."
    )
    model = NotificationSettings
    node_overrides = {"email_from": EmailNode}
    required_permissions = frozenset({"admin.settings.edit"})


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec(NotificationsSpec)
