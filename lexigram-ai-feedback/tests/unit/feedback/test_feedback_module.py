"""Tests for feedback module."""

from __future__ import annotations

import pytest

from lexigram.ai.feedback import FeedbackModule
from lexigram.contracts.ai.feedback import FeedbackProtocol
from lexigram.di.module import DynamicModule


class TestFeedbackModule:
    """Test suite for FeedbackModule."""

    def test_module_decorator_exists(self) -> None:
        """Verify @module decorator is applied to FeedbackModule."""
        assert hasattr(FeedbackModule, '__lexigram_module__')

    def test_configure_returns_dynamic_module(self) -> None:
        """Verify configure() returns DynamicModule instance."""
        result = FeedbackModule.configure(None)
        assert isinstance(result, DynamicModule)
        assert result.module is FeedbackModule

    def test_configure_exports_feedback_protocol(self) -> None:
        """Verify configure() exports FeedbackProtocol."""
        result = FeedbackModule.configure(None)
        assert FeedbackProtocol in result.exports

    def test_configure_with_dict_config(self) -> None:
        """Verify configure() accepts dict configuration."""
        config = {"storage": "database"}
        result = FeedbackModule.configure(config)
        assert isinstance(result, DynamicModule)
        assert result.module is FeedbackModule
