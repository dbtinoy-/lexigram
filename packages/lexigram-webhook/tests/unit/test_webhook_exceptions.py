"""Tests for webhook exceptions module."""

from __future__ import annotations
from enum import Enum

import pytest

from lexigram.contracts.webhook.exceptions import WebhookError

from lexigram.webhook.exceptions import (
    DeliveryAttemptNotFoundError,
    InvalidWebhookURLError,
    SecretRotationError,
    SubscriptionInactiveError,
    SubscriptionNotFoundError,
)


class TestSubscriptionNotFoundError:
    """Tests for SubscriptionNotFoundError."""

    def test_inherits_from_webhook_error(self) -> None:
        """SubscriptionNotFoundError inherits from WebhookError."""
        assert issubclass(SubscriptionNotFoundError, WebhookError)

    def test_error_code(self) -> None:
        """SubscriptionNotFoundError has correct error code."""
        assert SubscriptionNotFoundError._code == "LEX_ERR_WEBHOOK_002"

    def test_can_be_instantiated(self) -> None:
        """SubscriptionNotFoundError can be instantiated with message."""
        err = SubscriptionNotFoundError("test message")
        assert "test message" in str(err)

    def test_can_be_raised_and_caught(self) -> None:
        """SubscriptionNotFoundError can be raised and caught."""
        with pytest.raises(SubscriptionNotFoundError):
            raise SubscriptionNotFoundError("test")


class TestSubscriptionInactiveError:
    """Tests for SubscriptionInactiveError."""

    def test_inherits_from_webhook_error(self) -> None:
        """SubscriptionInactiveError inherits from WebhookError."""
        assert issubclass(SubscriptionInactiveError, WebhookError)

    def test_error_code(self) -> None:
        """SubscriptionInactiveError has correct error code."""
        assert SubscriptionInactiveError._code == "LEX_ERR_WEBHOOK_003"

    def test_can_be_instantiated(self) -> None:
        """SubscriptionInactiveError can be instantiated with message."""
        err = SubscriptionInactiveError("test message")
        assert "test message" in str(err)

    def test_can_be_raised_and_caught(self) -> None:
        """SubscriptionInactiveError can be raised and caught."""
        with pytest.raises(SubscriptionInactiveError):
            raise SubscriptionInactiveError("test")


class TestInvalidWebhookURLError:
    """Tests for InvalidWebhookURLError."""

    def test_inherits_from_webhook_error(self) -> None:
        """InvalidWebhookURLError inherits from WebhookError."""
        assert issubclass(InvalidWebhookURLError, WebhookError)

    def test_error_code(self) -> None:
        """InvalidWebhookURLError has correct error code."""
        assert InvalidWebhookURLError._code == "LEX_ERR_WEBHOOK_004"

    def test_can_be_instantiated(self) -> None:
        """InvalidWebhookURLError can be instantiated with message."""
        err = InvalidWebhookURLError("test message")
        assert "test message" in str(err)

    def test_can_be_raised_and_caught(self) -> None:
        """InvalidWebhookURLError can be raised and caught."""
        with pytest.raises(InvalidWebhookURLError):
            raise InvalidWebhookURLError("test")


class TestDeliveryAttemptNotFoundError:
    """Tests for DeliveryAttemptNotFoundError."""

    def test_inherits_from_webhook_error(self) -> None:
        """DeliveryAttemptNotFoundError inherits from WebhookError."""
        assert issubclass(DeliveryAttemptNotFoundError, WebhookError)

    def test_error_code(self) -> None:
        """DeliveryAttemptNotFoundError has correct error code."""
        assert DeliveryAttemptNotFoundError._code == "LEX_ERR_WEBHOOK_005"

    def test_can_be_instantiated(self) -> None:
        """DeliveryAttemptNotFoundError can be instantiated with message."""
        err = DeliveryAttemptNotFoundError("test message")
        assert "test message" in str(err)

    def test_can_be_raised_and_caught(self) -> None:
        """DeliveryAttemptNotFoundError can be raised and caught."""
        with pytest.raises(DeliveryAttemptNotFoundError):
            raise DeliveryAttemptNotFoundError("test")


class TestSecretRotationError:
    """Tests for SecretRotationError."""

    def test_inherits_from_webhook_error(self) -> None:
        """SecretRotationError inherits from WebhookError."""
        assert issubclass(SecretRotationError, WebhookError)

    def test_error_code(self) -> None:
        """SecretRotationError has correct error code."""
        assert SecretRotationError._code == "LEX_ERR_WEBHOOK_006"

    def test_can_be_instantiated(self) -> None:
        """SecretRotationError can be instantiated with message."""
        err = SecretRotationError("test message")
        assert "test message" in str(err)

    def test_can_be_raised_and_caught(self) -> None:
        """SecretRotationError can be raised and caught."""
        with pytest.raises(SecretRotationError):
            raise SecretRotationError("test")


class TestExceptionAllExports:
    """Tests for __all__ exports."""

    def test_all_contains_expected_items(self) -> None:
        """__all__ contains all expected exports."""
        from lexigram.webhook import exceptions
        expected = [
            "DeliveryAttemptNotFoundError",
            "InvalidWebhookURLError",
            "SecretRotationError",
            "SubscriptionInactiveError",
            "SubscriptionNotFoundError",
        ]
        for item in expected:
            assert item in exceptions.__all__
