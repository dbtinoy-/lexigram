"""Unit tests for di provider."""

import pytest
from lexigram.ai.evaluation.di.provider import EvaluationProvider


class TestEvaluationProvider:
    """Tests for EvaluationProvider."""

    def test_provider_creation(self) -> None:
        """Test provider can be created."""
        provider = EvaluationProvider()
        assert provider is not None

    def test_provider_name(self) -> None:
        """Test provider has correct name."""
        provider = EvaluationProvider()
        assert provider.name == "evaluation"

    def test_provider_priority(self) -> None:
        """Test provider has priority."""
        provider = EvaluationProvider()
        assert hasattr(provider, "priority")

    def test_provider_register(self) -> None:
        """Test provider has register method."""
        provider = EvaluationProvider()
        assert hasattr(provider, "register")
        assert callable(provider.register)

    def test_provider_boot(self) -> None:
        """Test provider has boot method."""
        provider = EvaluationProvider()
        assert hasattr(provider, "boot")
        assert callable(provider.boot)

    def test_provider_shutdown(self) -> None:
        """Test provider has shutdown method."""
        provider = EvaluationProvider()
        assert hasattr(provider, "shutdown")
        assert callable(provider.shutdown)