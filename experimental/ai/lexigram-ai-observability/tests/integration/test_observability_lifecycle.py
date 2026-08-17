"""Integration tests for lexigram-ai-observability package."""

from __future__ import annotations

import pytest

from lexigram.ai.observability.config import ObservabilityConfig


class TestObservabilityConfigIntegration:
    """Integration tests for ObservabilityConfig."""

    @pytest.mark.integration
    def test_observability_config_creation(self):
        """Test ObservabilityConfig can be created."""
        config = ObservabilityConfig()
        assert config is not None

    @pytest.mark.integration
    def test_observability_config_model_dump(self):
        """Test ObservabilityConfig model can be serialized."""
        config = ObservabilityConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)

    @pytest.mark.integration
    def test_observability_config_has_enabled(self):
        """Test ObservabilityConfig has enabled field."""
        config = ObservabilityConfig()
        assert hasattr(config, "enabled")


class TestAIObservabilityIntegration:
    """Integration tests for AI observability components."""

    @pytest.mark.integration
    def test_ai_metrics_import(self):
        """Test AIMetrics can be imported."""
        from lexigram.ai.observability.metrics import AIMetrics
        assert AIMetrics is not None

    @pytest.mark.integration
    def test_ai_tracer_import(self):
        """Test AITracer can be imported."""
        from lexigram.ai.observability.tracing import AITracer
        assert AITracer is not None

    @pytest.mark.integration
    def test_ai_health_monitor_import(self):
        """Test AIHealthMonitor can be imported."""
        from lexigram.ai.observability.health import AIHealthMonitor
        assert AIHealthMonitor is not None


class TestObservabilityProtocolsIntegration:
    """Integration tests for observability protocols."""

    @pytest.mark.integration
    def test_ai_metrics_protocol_import(self):
        """Test AIMetricsProtocol can be imported."""
        from lexigram.contracts.observability.ai import AIMetricsProtocol
        assert AIMetricsProtocol is not None

    @pytest.mark.integration
    def test_ai_tracer_protocol_import(self):
        """Test AITracerProtocol can be imported."""
        from lexigram.contracts.observability.ai import AITracerProtocol
        assert AITracerProtocol is not None

    @pytest.mark.integration
    def test_ai_health_monitor_protocol_import(self):
        """Test AIHealthMonitorProtocol can be imported."""
        from lexigram.contracts.observability.ai import AIHealthMonitorProtocol
        assert AIHealthMonitorProtocol is not None


class TestObservabilityModuleIntegration:
    """Integration tests for ObservabilityModule."""

    @pytest.mark.integration
    def test_observability_module_import(self):
        """Test ObservabilityModule can be imported."""
        from lexigram.ai.observability.module import ObservabilityModule
        assert ObservabilityModule is not None