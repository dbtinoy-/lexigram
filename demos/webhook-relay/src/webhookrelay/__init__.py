"""Webhook relay demo — Lexigram subscriptions and HMAC verification.

The public surface is intentionally small: a standalone application factory,
its typed ingress config, and the lifecycle provider that composes the
package services with the browser event ledger.
"""

from __future__ import annotations

from webhookrelay.app import create_app
from webhookrelay.config import WebhookRelayConfig
from webhookrelay.di.provider import WebhookRelayProvider

__all__ = [
    "WebhookRelayConfig",
    "WebhookRelayProvider",
    "create_app",
]
