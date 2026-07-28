"""Notification template generator."""

from __future__ import annotations

from lexigram.codegen.base import TemplateGeneratorBase


class NotificationTemplateGenerator(TemplateGeneratorBase):
    """Generator for notification templates."""

    name = "notification_template"
    description = "Generate a notification template"

    def generate(self, context: dict[str, object]) -> list[object]:
        """Generate notification template files."""
        raise NotImplementedError("NotificationTemplateGenerator not yet implemented")
