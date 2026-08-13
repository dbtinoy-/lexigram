"""Integration tests for lexigram-resilience package lifecycle."""

from __future__ import annotations

import pytest

from lexigram.resilience.config import IdempotencyConfig
from lexigram.resilience.idempotency.provider import IdempotencyProvider


class TestIdempotencyProviderIntegration:
    """Integration tests for IdempotencyProvider basic functionality."""

    @pytest.mark.integration
    def test_provider_initialization_default(self):
        """Test IdempotencyProvider initialization with default config."""
        provider = IdempotencyProvider()
        assert provider.name == "idempotency"

    @pytest.mark.integration
    def test_provider_initialization_with_config(self):
        """Test IdempotencyProvider initialization with custom config."""
        config = IdempotencyConfig()
        provider = IdempotencyProvider(config=config)
        assert provider.name == "idempotency"

    @pytest.mark.integration
    def test_provider_has_required_attributes(self):
        """Test provider has required attributes."""
        provider = IdempotencyProvider()
        assert hasattr(provider, "name")

    @pytest.mark.integration
    def test_provider_priority(self):
        """Test provider has correct priority."""
        from lexigram.contracts.core.provider import ProviderPriority
        provider = IdempotencyProvider()
        assert provider.priority == ProviderPriority.INFRASTRUCTURE


class TestIdempotencyConfigIntegration:
    """Integration tests for IdempotencyConfig."""

    @pytest.mark.integration
    def test_config_creation(self):
        """Test IdempotencyConfig can be created."""
        config = IdempotencyConfig()
        assert config is not None

    @pytest.mark.integration
    def test_config_model_dump(self):
        """Test IdempotencyConfig model can be serialized."""
        config = IdempotencyConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)

    @pytest.mark.integration
    def test_config_has_ttl(self):
        """Test IdempotencyConfig has ttl field."""
        config = IdempotencyConfig(ttl=300)
        assert config.ttl == 300

    @pytest.mark.integration
    def test_config_has_max_entries(self):
        """Test IdempotencyConfig has max_entries field."""
        config = IdempotencyConfig(max_entries=1000)
        assert config.max_entries == 1000


class TestResilienceModuleIntegration:
    """Integration tests for ResilienceModule."""

    @pytest.mark.integration
    def test_resilience_module_import(self):
        """Test ResilienceModule can be imported."""
        from lexigram.resilience.module import ResilienceModule
        assert ResilienceModule is not None


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker."""

    @pytest.mark.integration
    def test_circuit_breaker_import(self):
        """Test CircuitBreaker can be imported."""
        from lexigram.resilience.circuit import CircuitBreaker
        assert CircuitBreaker is not None