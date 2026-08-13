"""Tests for lexigram-webhook module."""

import pytest

from lexigram import webhook as webhook_module


class TestWebhookModule:
    """Test basic webhook module structure."""

    def test_module_imports(self):
        """Test module can be imported."""
        assert webhook_module is not None

    def test_module_has_name(self):
        """Test module has __name__."""
        assert webhook_module.__name__ == "lexigram.webhook"

    def test_module_in_lexigram_packages(self):
        """Test webhook is in lexigram packages."""
        import lexigram
        assert hasattr(lexigram, "webhook")


class TestWebhookSubmodules:
    """Test webhook submodules exist."""

    def test_delivery_module(self):
        from lexigram.webhook import delivery
        assert delivery is not None

    def test_store_module(self):
        from lexigram.webhook import store
        assert store is not None

    def test_config_module(self):
        from lexigram.webhook import config
        assert config is not None

    def test_types_module(self):
        from lexigram.webhook import types
        assert types is not None