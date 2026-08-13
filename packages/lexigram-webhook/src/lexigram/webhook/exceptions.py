"""Webhook package-level exception hierarchy."""

from __future__ import annotations

from lexigram.contracts.webhook.exceptions import WebhookError


class SubscriptionNotFoundError(WebhookError):
    """Raised when a subscription ID is not found."""

    _code = "LEX_ERR_WEBHOOK_002"


class SubscriptionInactiveError(WebhookError):
    """Raised when attempting to deliver to a deactivated subscription."""

    _code = "LEX_ERR_WEBHOOK_003"


class InvalidWebhookURLError(WebhookError):
    """Raised when a subscription URL fails validation."""

    _code = "LEX_ERR_WEBHOOK_004"


class DeliveryAttemptNotFoundError(WebhookError):
    """Raised when a delivery attempt ID is not found."""

    _code = "LEX_ERR_WEBHOOK_005"


class SecretRotationError(WebhookError):
    """Raised when secret rotation fails."""

    _code = "LEX_ERR_WEBHOOK_006"


__all__ = [
    "DeliveryAttemptNotFoundError",
    "InvalidWebhookURLError",
    "SecretRotationError",
    "SubscriptionInactiveError",
    "SubscriptionNotFoundError",
]
