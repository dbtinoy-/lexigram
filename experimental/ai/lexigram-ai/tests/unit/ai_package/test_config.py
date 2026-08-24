"""Tests for lexigram.ai.config."""

from __future__ import annotations

import pytest


class TestGetSubsystemConfig:
    """Tests for lexigram.ai.config.get_subsystem_config."""

    def test_returns_known_field_when_set(self) -> None:
        from lexigram.ai.config import AIConfig, get_subsystem_config

        try:
            from lexigram.ai.config import ClientConfig as LLMConfig
        except ImportError:
            pytest.skip("lexigram-ai-llm not installed")

        config = AIConfig(llm=LLMConfig(provider="openai", model="gpt-4o"))
        result = get_subsystem_config(config, "llm")
        assert result is config.llm

    def test_returns_default_when_field_is_none(self) -> None:
        from lexigram.ai.config import AIConfig, get_subsystem_config

        config = AIConfig()
        result = get_subsystem_config(config, "llm", default="SENTINEL")
        assert result == "SENTINEL"

    def test_returns_dynamic_subsystem_from_dict(self) -> None:
        from lexigram.ai.config import AIConfig, get_subsystem_config

        config = AIConfig(subsystems={"fine_tuning": {"epochs": 5}})
        result = get_subsystem_config(config, "fine_tuning")
        assert result == {"epochs": 5}

    def test_returns_default_for_unknown_subsystem(self) -> None:
        from lexigram.ai.config import AIConfig, get_subsystem_config

        config = AIConfig()
        result = get_subsystem_config(config, "nonexistent_subsystem", default=42)
        assert result == 42

    def test_returns_none_default_when_not_specified(self) -> None:
        from lexigram.ai.config import AIConfig, get_subsystem_config

        config = AIConfig()
        result = get_subsystem_config(config, "rag")
        assert result is None


class TestAIConfig:
    """Tests for AIConfig defaults and field behaviour."""

    def test_default_config_enabled(self) -> None:
        from lexigram.ai.config import AIConfig

        config = AIConfig()
        assert config.enabled is True

    def test_default_config_no_llm(self) -> None:
        from lexigram.ai.config import AIConfig

        config = AIConfig()
        assert config.llm is None

    def test_default_config_no_vector(self) -> None:
        from lexigram.ai.config import AIConfig

        config = AIConfig()
        assert config.vector is None

    def test_default_config_no_rag(self) -> None:
        from lexigram.ai.config import AIConfig

        config = AIConfig()
        assert config.rag is None

    def test_subsystems_default_empty(self) -> None:
        from lexigram.ai.config import AIConfig

        config = AIConfig()
        assert config.subsystems == {}

    def test_config_name_default(self) -> None:
        from lexigram.ai.config import AIConfig

        config = AIConfig()
        assert config.name == "ai"

    def test_provider_class_is_ai_provider(self) -> None:
        from lexigram.ai.config import AIConfig
        from lexigram.ai.di.provider import AIProvider

        assert AIConfig.get_provider_class() is AIProvider

    def test_production_security_validator_blocks_insecure_key(self, monkeypatch) -> None:
        from lexigram.ai.config import AIConfig
        try:
            from lexigram.ai.llm.config import ClientConfig as LLMConfig
            from pydantic import SecretStr
        except ImportError:
            pytest.skip("lexigram-ai-llm or pydantic not installed")

        monkeypatch.setenv("LEX_ENV", "production")

        with pytest.raises(ValueError, match="CRITICAL SECURITY ERROR"):
            AIConfig(llm=LLMConfig(provider="openai", model="gpt-4", api_key=SecretStr("sk-...")))

    def test_production_security_validator_allows_secure_key(self, monkeypatch) -> None:
        from lexigram.ai.config import AIConfig
        try:
            from lexigram.ai.llm.config import ClientConfig as LLMConfig
            from pydantic import SecretStr
        except ImportError:
            pytest.skip("lexigram-ai-llm or pydantic not installed")

        monkeypatch.setenv("LEX_ENV", "production")

        config = AIConfig(llm=LLMConfig(provider="openai", model="gpt-4", api_key=SecretStr("sk-real-key-1234567890")))
        assert config.llm.api_key.get_secret_value() == "sk-real-key-1234567890"

    def test_production_security_validator_ignored_in_dev(self, monkeypatch) -> None:
        from lexigram.ai.config import AIConfig
        try:
            from lexigram.ai.llm.config import ClientConfig as LLMConfig
            from pydantic import SecretStr
        except ImportError:
            pytest.skip("lexigram-ai-llm or pydantic not installed")

        monkeypatch.setenv("LEX_ENV", "development")

        config = AIConfig(llm=LLMConfig(provider="openai", model="gpt-4", api_key=SecretStr("sk-...")))
        assert config.llm.api_key.get_secret_value() == "sk-..."
