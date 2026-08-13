"""Tests for WebhookConfig defaults and immutability."""

from __future__ import annotations
from enum import Enum

import pytest

from lexigram.webhook.config import WebhookConfig


class TestWebhookConfig:
    """Tests for WebhookConfig."""

    def test_default_values(self) -> None:
        """Config has expected defaults."""
        cfg = WebhookConfig()
        assert cfg.store_backend == "memory"
        assert cfg.retry_max_attempts == 5
        assert cfg.retry_base_delay == 1.0
        assert cfg.retry_max_delay == 60.0
        assert cfg.retry_backoff_factor == 2.0
        assert cfg.secret_length == 32
        assert cfg.secret_rotation_grace_hours == 24
        assert cfg.delivery_timeout_seconds == 30.0
        assert cfg.disable_after_consecutive_failures == 50
        assert cfg.failure_window_hours == 24
        assert cfg.signature_algorithm == "sha256"
        assert cfg.enable_admin is True
        assert cfg.delivery_log_retention_days == 30
        assert cfg.signature_header == "X-Webhook-Signature"
        assert cfg.event_type_header == "X-Webhook-Event-Type"
        assert cfg.event_id_header == "X-Webhook-Event-ID"
        assert cfg.timestamp_header == "X-Webhook-Timestamp"

    def test_custom_values(self) -> None:
        """Custom values are stored correctly."""
        cfg = WebhookConfig(
            store_backend="sql",
            retry_max_attempts=3,
            enable_admin=False,
        )
        assert cfg.store_backend == "sql"
        assert cfg.retry_max_attempts == 3
        assert cfg.enable_admin is False
