"""Integration tests for lexigram-ai-safety package."""

from __future__ import annotations

import pytest

from lexigram.ai.guard.config import GuardConfig
from lexigram.ai.guard.di.provider import GuardProvider


class TestGuardProviderIntegration:
    """Integration tests for GuardProvider basic functionality."""

    @pytest.mark.integration
    def test_provider_initialization_default(self):
        """Test GuardProvider initialization with default config."""
        provider = GuardProvider()
        assert provider.name == "guard"

    @pytest.mark.integration
    def test_provider_initialization_with_config(self):
        """Test GuardProvider initialization with custom config."""
        config = GuardConfig()
        provider = GuardProvider(config=config)
        assert provider.name == "guard"

    @pytest.mark.integration
    def test_provider_has_required_attributes(self):
        """Test provider has required attributes."""
        provider = GuardProvider()
        assert hasattr(provider, "name")

    @pytest.mark.integration
    def test_provider_priority(self):
        """Test provider has correct priority."""
        from lexigram.contracts.core.provider import ProviderPriority
        provider = GuardProvider()
        assert provider.priority == ProviderPriority.SECURITY


class TestGuardConfigIntegration:
    """Integration tests for GuardConfig."""

    @pytest.mark.integration
    def test_guard_config_creation(self):
        """Test GuardConfig can be created."""
        config = GuardConfig()
        assert config is not None

    @pytest.mark.integration
    def test_guard_config_model_dump(self):
        """Test GuardConfig model can be serialized."""
        config = GuardConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)

    @pytest.mark.integration
    def test_guard_config_has_enabled(self):
        """Test GuardConfig has enabled field."""
        config = GuardConfig()
        assert hasattr(config, "enabled")


class TestGuardModuleIntegration:
    """Integration tests for GuardModule."""

    @pytest.mark.integration
    def test_guard_module_import(self):
        """Test GuardModule can be imported."""
        from lexigram.ai.guard.module import GuardModule
        assert GuardModule is not None


class TestGuardPipelineIntegration:
    """Integration tests for guard pipeline."""

    @pytest.mark.integration
    def test_guard_pipeline_import(self):
        """Test GuardPipeline can be imported."""
        from lexigram.ai.guard.pipeline.guard_pipeline import GuardPipeline
        assert GuardPipeline is not None


class TestInputGuardsIntegration:
    """Integration tests for input guards."""

    @pytest.mark.integration
    def test_prompt_injection_detector_import(self):
        """Test PromptInjectionDetector can be imported."""
        from lexigram.ai.guard.input.injection import PromptInjectionDetector
        assert PromptInjectionDetector is not None

    @pytest.mark.integration
    def test_llm_injection_detector_import(self):
        """Test LLMInjectionDetector can be imported."""
        from lexigram.ai.guard.input.llm_injection import LLMInjectionDetector
        assert LLMInjectionDetector is not None

    @pytest.mark.integration
    def test_llm_jailbreak_detector_import(self):
        """Test LLMJailbreakDetector can be imported."""
        from lexigram.ai.guard.input.llm_jailbreak import LLMJailbreakDetector
        assert LLMJailbreakDetector is not None

    @pytest.mark.integration
    def test_pii_detector_import(self):
        """Test PIIDetector can be imported."""
        from lexigram.ai.guard.input.pii import PIIDetector
        assert PIIDetector is not None


class TestOutputGuardsIntegration:
    """Integration tests for output guards."""

    @pytest.mark.integration
    def test_output_length_guard_import(self):
        """Test OutputLengthGuard can be imported."""
        from lexigram.ai.guard.output.length import OutputLengthGuard
        assert OutputLengthGuard is not None

    @pytest.mark.integration
    def test_pii_redactor_import(self):
        """Test PIIRedactor can be imported."""
        from lexigram.ai.guard.output.pii_redactor import PIIRedactor
        assert PIIRedactor is not None


class TestGuardProtocolsIntegration:
    """Integration tests for guard protocols."""

    @pytest.mark.integration
    def test_input_guard_protocol_import(self):
        """Test InputGuardProtocol can be imported."""
        from lexigram.contracts.ai.guards import InputGuardProtocol
        assert InputGuardProtocol is not None

    @pytest.mark.integration
    def test_output_guard_protocol_import(self):
        """Test OutputGuardProtocol can be imported."""
        from lexigram.contracts.ai.guards import OutputGuardProtocol
        assert OutputGuardProtocol is not None