"""Outbound webhook delivery for lexigram-events."""

from __future__ import annotations

from lexigram.events.webhooks.dispatcher import WebhookDispatcher, WebhookEndpoint

__all__ = ["WebhookDispatcher", "WebhookEndpoint"]
