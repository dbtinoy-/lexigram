"""Tests for webhook secret generation."""

from __future__ import annotations

import pytest

from lexigram.webhook.subscription.secret import generate_webhook_secret


class TestGenerateWebhookSecret:
    """Tests for generate_webhook_secret function."""

    def test_generates_hex_string(self) -> None:
        """generate_webhook_secret returns hex-encoded string."""
        secret = generate_webhook_secret()
        assert isinstance(secret, str)
        assert all(c in "0123456789abcdef" for c in secret)

    def test_default_length_produces_64_char_hex(self) -> None:
        """Default length produces 64 character hex (32 bytes)."""
        secret = generate_webhook_secret()
        assert len(secret) == 64

    def test_custom_length_32(self) -> None:
        """Custom length 32 produces 64 character hex."""
        secret = generate_webhook_secret(32)
        assert len(secret) == 64

    def test_custom_length_16(self) -> None:
        """Custom length 16 produces 32 character hex."""
        secret = generate_webhook_secret(16)
        assert len(secret) == 32

    def test_custom_length_64(self) -> None:
        """Custom length 64 produces 128 character hex."""
        secret = generate_webhook_secret(64)
        assert len(secret) == 128

    def test_each_call_produces_unique_secret(self) -> None:
        """Each call produces a unique secret."""
        secrets = [generate_webhook_secret() for _ in range(100)]
        assert len(set(secrets)) == 100

    def test_output_is_different_from_input(self) -> None:
        """Secret is different from input length value."""
        secret = generate_webhook_secret(16)
        # The secret is hex-encoded, so it's impossible to equal "16"
        # This is more of a sanity check
        assert secret != "16"


class TestSecretModuleExports:
    """Tests for module exports."""

    def test_all_contains_generate_webhook_secret(self) -> None:
        """__all__ contains generate_webhook_secret."""
        from lexigram.webhook.subscription import secret
        assert "generate_webhook_secret" in secret.__all__

    def test_module_imports(self) -> None:
        """Module can be imported."""
        from lexigram.webhook import subscription
        assert subscription.secret is not None