"""Webhook relay demo — HMAC signing and payload validation.

Convention followed: **Package exports** — ``__init__.py`` re-exports
the public API surface without defining logic.

Exports:

- ``create_app`` — composition root for the application
- ``WebhookRelayConfig`` — demo configuration model
- ``WebhookRelayProvider`` — DI provider for webhook relay services
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
