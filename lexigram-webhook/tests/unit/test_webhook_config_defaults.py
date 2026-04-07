"""Tests for webhook config defaults."""

from __future__ import annotations

from lexigram.webhook.config import WebhookConfig
from lexigram.webhook import constants as const


class TestWebhookConfigDefaults:
    """Tests for WebhookConfig default values."""

    def test_retry_max_attempts_default(self) -> None:
        """Default retry_max_attempts is 5."""
        config = WebhookConfig()
        assert config.retry_max_attempts == const.DEFAULT_RETRY_MAX_ATTEMPTS

    def test_retry_base_delay_default(self) -> None:
        """Default retry_base_delay is 1.0 seconds."""
        config = WebhookConfig()
        assert config.retry_base_delay == const.DEFAULT_RETRY_BASE_DELAY

    def test_retry_max_delay_default(self) -> None:
        """Default retry_max_delay is 60.0 seconds."""
        config = WebhookConfig()
        assert config.retry_max_delay == const.DEFAULT_RETRY_MAX_DELAY

    def test_retry_backoff_factor_default(self) -> None:
        """Default retry_backoff_factor is 2.0."""
        config = WebhookConfig()
        assert config.retry_backoff_factor == const.DEFAULT_RETRY_BACKOFF_FACTOR

    def test_delivery_timeout_seconds_default(self) -> None:
        """Default delivery_timeout_seconds is 30.0."""
        config = WebhookConfig()
        assert config.delivery_timeout_seconds == const.DEFAULT_DELIVERY_TIMEOUT_SECONDS

    def test_signature_header_default(self) -> None:
        """Default signature_header is X-Webhook-Signature."""
        config = WebhookConfig()
        assert config.signature_header == const.DEFAULT_SIGNATURE_HEADER

    def test_event_type_header_default(self) -> None:
        """Default event_type_header is X-Webhook-Event-Type."""
        config = WebhookConfig()
        assert config.event_type_header == const.DEFAULT_EVENT_TYPE_HEADER

    def test_event_id_header_default(self) -> None:
        """Default event_id_header is X-Webhook-Event-ID."""
        config = WebhookConfig()
        assert config.event_id_header == const.DEFAULT_EVENT_ID_HEADER

    def test_timestamp_header_default(self) -> None:
        """Default timestamp_header is X-Webhook-Timestamp."""
        config = WebhookConfig()
        assert config.timestamp_header == const.DEFAULT_TIMESTAMP_HEADER

    def test_secret_length_default(self) -> None:
        """Default secret_length is 32."""
        config = WebhookConfig()
        assert config.secret_length == const.DEFAULT_SECRET_LENGTH

    def test_secret_rotation_grace_hours_default(self) -> None:
        """Default secret_rotation_grace_hours is 24."""
        config = WebhookConfig()
        assert config.secret_rotation_grace_hours == const.DEFAULT_SECRET_ROTATION_GRACE_HOURS

    def test_disable_after_consecutive_failures_default(self) -> None:
        """Default disable_after_consecutive_failures is 50."""
        config = WebhookConfig()
        assert config.disable_after_consecutive_failures == const.DEFAULT_DISABLE_AFTER_CONSECUTIVE_FAILURES

    def test_failure_window_hours_default(self) -> None:
        """Default failure_window_hours is 24."""
        config = WebhookConfig()
        assert config.failure_window_hours == const.DEFAULT_FAILURE_WINDOW_HOURS