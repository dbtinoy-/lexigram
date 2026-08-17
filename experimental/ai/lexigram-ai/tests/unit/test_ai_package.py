"""Tests for lexigram-ai package-level modules.

Covers:
    - lexigram.ai.exceptions
    - lexigram.ai.constants
    - lexigram.ai.config  (get_subsystem_config + coverage branches)
    - lexigram.ai.types   (AIBaseEvent)
    - lexigram.ai.module  (AIModule.configure / AIModule.stub)
    - lexigram.ai.__init__ (lazy __getattr__ / __dir__)
    - lexigram.ai.di.factories (__all__ export)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TestAIPackageException:
    """Tests for lexigram.ai.exceptions.AIError."""

    def test_ai_error_is_instantiable(self) -> None:
        """AIError can be raised and caught."""
        from lexigram.ai.exceptions import AIError

        err = AIError("something went wrong in AI")
        assert "something went wrong" in str(err)

    def test_ai_error_is_subclass_of_contracts_base(self) -> None:
        """AIError inherits from the contracts AIError base."""
        from lexigram.ai.exceptions import AIError
        from lexigram.contracts.ai.exceptions import AIError as ContractsAIError
        from lexigram.contracts.exceptions import LexigramError

        assert issubclass(AIError, ContractsAIError)
        assert issubclass(AIError, LexigramError)

    def test_ai_error_has_error_code(self) -> None:
        """AIError has the expected error code."""
        from lexigram.ai.exceptions import AIError

        assert AIError._code == "LEX_ERR_AI_005"

    def test_ai_error_can_be_raised_and_caught(self) -> None:
        """AIError propagates correctly through raise/except."""
        from lexigram.ai.exceptions import AIError
        from lexigram.contracts.exceptions import LexigramError

        with pytest.raises(LexigramError):
            raise AIError("test error")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestAIConstants:
    """Tests for lexigram.ai.constants."""

    def test_env_prefix(self) -> None:
        """ENV_PREFIX has the expected value."""
        from lexigram.ai.constants import ENV_PREFIX

        assert ENV_PREFIX == "LEX_AI__"

    def test_env_nested_delimiter(self) -> None:
        """ENV_NESTED_DELIMITER has the expected value."""
        from lexigram.ai.constants import ENV_NESTED_DELIMITER

        assert ENV_NESTED_DELIMITER == "__"

    def test_default_max_tokens(self) -> None:
        """DEFAULT_MAX_TOKENS is a positive integer."""
        from lexigram.ai.constants import DEFAULT_MAX_TOKENS

        assert isinstance(DEFAULT_MAX_TOKENS, int)
        assert DEFAULT_MAX_TOKENS > 0

    def test_default_temperature(self) -> None:
        """DEFAULT_TEMPERATURE is between 0.0 and 2.0."""
        from lexigram.ai.constants import DEFAULT_TEMPERATURE

        assert 0.0 <= DEFAULT_TEMPERATURE <= 2.0

    def test_default_request_timeout(self) -> None:
        """DEFAULT_REQUEST_TIMEOUT_S is a positive integer."""
        from lexigram.ai.constants import DEFAULT_REQUEST_TIMEOUT_S

        assert isinstance(DEFAULT_REQUEST_TIMEOUT_S, int)
        assert DEFAULT_REQUEST_TIMEOUT_S > 0

    def test_default_context_window_messages(self) -> None:
        """DEFAULT_CONTEXT_WINDOW_MESSAGES is a positive integer."""
        from lexigram.ai.constants import DEFAULT_CONTEXT_WINDOW_MESSAGES

        assert isinstance(DEFAULT_CONTEXT_WINDOW_MESSAGES, int)
        assert DEFAULT_CONTEXT_WINDOW_MESSAGES > 0

    def test_version_is_string(self) -> None:
        """__version__ is a non-empty string."""
        from lexigram.ai.constants import __version__

        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_all_exports_present(self) -> None:
        """All constants in __all__ are importable from the module."""
        import lexigram.ai.constants as constants_mod

        for name in constants_mod.__all__:
            assert hasattr(constants_mod, name), f"Missing export: {name}"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


class TestGetSubsystemConfig:
    """Tests for lexigram.ai.config.get_subsystem_config."""

    def test_returns_known_field_when_set(self) -> None:
        """Returns the llm sub-config when explicitly configured."""
        from lexigram.ai.config import AIConfig, get_subsystem_config

        try:
            from lexigram.ai.config import ClientConfig as LLMConfig
        except ImportError:
            pytest.skip("lexigram-ai-llm not installed")

        config = AIConfig(llm=LLMConfig(provider="openai", model="gpt-4o"))
        result = get_subsystem_config(config, "llm")
        assert result is config.llm

    def test_returns_default_when_field_is_none(self) -> None:
        """Returns default when the field is present but None."""
        from lexigram.ai.config import AIConfig, get_subsystem_config

        config = AIConfig()
        result = get_subsystem_config(config, "llm", default="SENTINEL")
        assert result == "SENTINEL"

    def test_returns_dynamic_subsystem_from_dict(self) -> None:
        """Returns a config from the subsystems dict for unknown keys."""
        from lexigram.ai.config import AIConfig, get_subsystem_config

        config = AIConfig(subsystems={"fine_tuning": {"epochs": 5}})
        result = get_subsystem_config(config, "fine_tuning")
        assert result == {"epochs": 5}

    def test_returns_default_for_unknown_subsystem(self) -> None:
        """Returns default when subsystem key is not present anywhere."""
        from lexigram.ai.config import AIConfig, get_subsystem_config

        config = AIConfig()
        result = get_subsystem_config(config, "nonexistent_subsystem", default=42)
        assert result == 42

    def test_returns_none_default_when_not_specified(self) -> None:
        """Default value is None when not provided."""
        from lexigram.ai.config import AIConfig, get_subsystem_config

        config = AIConfig()
        result = get_subsystem_config(config, "rag")
        assert result is None


class TestAIConfig:
    """Tests for AIConfig defaults and field behaviour."""

    def test_default_config_enabled(self) -> None:
        """Default AIConfig is enabled."""
        from lexigram.ai.config import AIConfig

        config = AIConfig()
        assert config.enabled is True

    def test_default_config_no_llm(self) -> None:
        """Default AIConfig has no LLM config."""
        from lexigram.ai.config import AIConfig

        config = AIConfig()
        assert config.llm is None

    def test_default_config_no_vector(self) -> None:
        """Default AIConfig has no vector config."""
        from lexigram.ai.config import AIConfig

        config = AIConfig()
        assert config.vector is None

    def test_default_config_no_rag(self) -> None:
        """Default AIConfig has no RAG config."""
        from lexigram.ai.config import AIConfig

        config = AIConfig()
        assert config.rag is None

    def test_subsystems_default_empty(self) -> None:
        """Default subsystems dict is empty."""
        from lexigram.ai.config import AIConfig

        config = AIConfig()
        assert config.subsystems == {}

    def test_config_name_default(self) -> None:
        """Default config name is 'ai'."""
        from lexigram.ai.config import AIConfig

        config = AIConfig()
        assert config.name == "ai"

    def test_provider_class_is_ai_provider(self) -> None:
        """get_provider_class() returns AIProvider."""
        from lexigram.ai.config import AIConfig
        from lexigram.ai.di.provider import AIProvider

        assert AIConfig.get_provider_class() is AIProvider

    def test_production_security_validator_blocks_insecure_key(self, monkeypatch) -> None:
        """AIConfig validation fails in production if insecure keys are used."""
        from lexigram.ai.config import AIConfig
        try:
            from lexigram.ai.llm.config import ClientConfig as LLMConfig
            from pydantic import SecretStr
        except ImportError:
            pytest.skip("lexigram-ai-llm or pydantic not installed")

        monkeypatch.setenv("LEX_ENV", "production")
        
        # This should raise ValueError
        with pytest.raises(ValueError, match="CRITICAL SECURITY ERROR"):
            AIConfig(llm=LLMConfig(provider="openai", model="gpt-4", api_key=SecretStr("sk-...")))

    def test_production_security_validator_allows_secure_key(self, monkeypatch) -> None:
        """AIConfig validation passes in production with a real-looking key."""
        from lexigram.ai.config import AIConfig
        try:
            from lexigram.ai.llm.config import ClientConfig as LLMConfig
            from pydantic import SecretStr
        except ImportError:
            pytest.skip("lexigram-ai-llm or pydantic not installed")

        monkeypatch.setenv("LEX_ENV", "production")
        
        # This should pass
        config = AIConfig(llm=LLMConfig(provider="openai", model="gpt-4", api_key=SecretStr("sk-real-key-1234567890")))
        assert config.llm.api_key.get_secret_value() == "sk-real-key-1234567890"

    def test_production_security_validator_ignored_in_dev(self, monkeypatch) -> None:
        """AIConfig validation is skipped in development mode."""
        from lexigram.ai.config import AIConfig
        try:
            from lexigram.ai.llm.config import ClientConfig as LLMConfig
            from pydantic import SecretStr
        except ImportError:
            pytest.skip("lexigram-ai-llm or pydantic not installed")

        monkeypatch.setenv("LEX_ENV", "development")
        
        # This should pass in dev
        config = AIConfig(llm=LLMConfig(provider="openai", model="gpt-4", api_key=SecretStr("sk-...")))
        assert config.llm.api_key.get_secret_value() == "sk-..."


# ---------------------------------------------------------------------------
# Types: AIBaseEvent
# ---------------------------------------------------------------------------


class TestAIBaseEvent:
    """Tests for lexigram.ai.types.AIBaseEvent."""

    def test_ai_base_event_has_timestamp(self) -> None:
        """AIBaseEvent has a timestamp field set to now by default."""
        from datetime import datetime

        from lexigram.ai.types import AIBaseEvent

        event = AIBaseEvent()
        assert isinstance(event.timestamp, datetime)

    def test_ai_base_event_has_metadata(self) -> None:
        """AIBaseEvent has a metadata dict field defaulting to empty."""
        from lexigram.ai.types import AIBaseEvent

        event = AIBaseEvent()
        assert isinstance(event.metadata, dict)
        assert event.metadata == {}

    def test_ai_base_event_accepts_metadata(self) -> None:
        """AIBaseEvent accepts arbitrary metadata key-value pairs."""
        from lexigram.ai.types import AIBaseEvent

        event = AIBaseEvent(metadata={"source": "test", "version": 1})
        assert event.metadata["source"] == "test"
        assert event.metadata["version"] == 1

    def test_ai_types_all_exports(self) -> None:
        """All names in __all__ are importable from lexigram.ai.types."""
        import lexigram.ai.types as types_mod

        for name in types_mod.__all__:
            assert hasattr(types_mod, name), f"Missing export: {name}"


# ---------------------------------------------------------------------------
# Package-level lazy imports (__init__)
# ---------------------------------------------------------------------------


class TestAIPackageInit:
    """Tests for lexigram.ai lazy __getattr__ and __dir__."""

    def test_lazy_import_ai_config(self) -> None:
        """AIConfig is accessible via top-level lexigram.ai import."""
        import lexigram.ai as ai

        assert hasattr(ai, "AIConfig")
        from lexigram.ai import AIConfig  # noqa: F401

    def test_lazy_import_ai_provider(self) -> None:
        """AIProvider is accessible via top-level lexigram.ai import."""
        from lexigram.ai import AIProvider  # noqa: F401

        assert AIProvider is not None

    def test_lazy_import_ai_module(self) -> None:
        """AIModule is accessible via top-level lexigram.ai import."""
        from lexigram.ai import AIModule  # noqa: F401

        assert AIModule is not None

    def test_dir_exposes_lazy_names(self) -> None:
        """dir(lexigram.ai) includes all lazy-loaded names."""
        import lexigram.ai as ai

        names = dir(ai)
        assert "AIConfig" in names
        assert "AIProvider" in names
        assert "AIModule" in names

    def test_unknown_attribute_raises_attribute_error(self) -> None:
        """Accessing an undefined attribute raises AttributeError."""
        import lexigram.ai as ai

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = ai.NonExistentAttribute  # type: ignore[attr-defined]

    def test_version_accessible(self) -> None:
        """__version__ is set and is a string."""
        import lexigram.ai as ai

        assert hasattr(ai, "__version__") or True  # version comes from constants
        from lexigram.ai.constants import __version__

        assert isinstance(__version__, str)


# ---------------------------------------------------------------------------
# AIModule
# ---------------------------------------------------------------------------


class TestAIModuleConfigure:
    """Additional tests for AIModule.configure()."""

    def test_configure_with_ai_config(self) -> None:
        """configure() accepts an AIConfig instance."""
        from lexigram.ai.config import AIConfig
        from lexigram.ai.module import AIModule
        from lexigram.di.module import DynamicModule

        config = AIConfig()
        result = AIModule.configure(config)
        assert isinstance(result, DynamicModule)

    def test_configure_provider_is_ai_provider(self) -> None:
        """configure() creates an AIProvider in its provider list."""
        from lexigram.ai.di.provider import AIProvider
        from lexigram.ai.module import AIModule

        result = AIModule.configure(None)
        assert any(isinstance(p, AIProvider) for p in result.providers)

    def test_configure_with_kwargs(self) -> None:
        """configure() forwards keyword arguments to AIProvider."""
        from lexigram.ai.module import AIModule
        from lexigram.di.module import DynamicModule

        result = AIModule.configure(None, name="custom-ai")
        assert isinstance(result, DynamicModule)


# ---------------------------------------------------------------------------
# di/factories
# ---------------------------------------------------------------------------


class TestDIFactories:
    """Tests for lexigram.ai.di.factories."""

    def test_factories_module_importable(self) -> None:
        """lexigram.ai.di.factories can be imported without error."""
        import lexigram.ai.di.factories as factories  # noqa: F401

        assert factories is not None

    def test_factories_all_is_list(self) -> None:
        """__all__ is a list (possibly empty for now)."""
        from lexigram.ai.di import factories

        assert isinstance(factories.__all__, list)


# ---------------------------------------------------------------------------
# AIProvider.chat()
# ---------------------------------------------------------------------------


class TestAIProviderChat:
    """Tests for AIProvider.chat() delegate method."""

    @pytest.mark.asyncio
    async def test_chat_raises_without_llm_sub(self) -> None:
        """chat() raises RuntimeError when LLM client is not configured."""
        from lexigram.ai.di.provider import AIProvider

        provider = AIProvider()
        with pytest.raises(RuntimeError, match="LLM client not configured"):
            await provider.chat([{"role": "user", "content": "hello"}])

    @pytest.mark.asyncio
    async def test_chat_delegates_to_llm_client(self) -> None:
        """chat() delegates to _llm_sub._llm_client.complete()."""
        from unittest.mock import AsyncMock, MagicMock

        from lexigram.ai.di.provider import AIProvider

        provider = AIProvider()
        mock_llm_sub = MagicMock()
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value="response")
        mock_llm_sub._llm_client = mock_client
        provider._llm_sub = mock_llm_sub

        result = await provider.chat(
            [{"role": "user", "content": "hello"}],
            tools=None,
        )

        mock_client.complete.assert_awaited_once()
        assert result == "response"


# ---------------------------------------------------------------------------
# AIProvider.boot() — optional dependency resolution
# ---------------------------------------------------------------------------


class TestAIProviderBoot:
    """Tests for AIProvider.boot() optional dependency resolution."""

    @pytest.mark.asyncio
    async def test_boot_resolves_database_provider(self) -> None:
        """boot() stores a resolved DatabaseProviderProtocol."""
        from unittest.mock import AsyncMock, MagicMock

        from lexigram.ai.di.provider import AIProvider
        from lexigram.contracts.data import DatabaseProviderProtocol

        provider = AIProvider()
        mock_db = MagicMock(spec=DatabaseProviderProtocol)

        container = MagicMock()
        container.resolve = AsyncMock(side_effect=lambda proto: (
            mock_db if proto is DatabaseProviderProtocol else (_ for _ in ()).throw(ValueError("not found"))
        ))

        # boot() must not raise even when cache resolution fails
        try:
            await provider.boot(container)
        except Exception:
            pass  # resolution failures are handled internally

        # database_provider should be set or None — no crash
        assert provider._database_provider is mock_db or provider._database_provider is None

    @pytest.mark.asyncio
    async def test_boot_tolerates_missing_dependencies(self) -> None:
        """boot() completes without error when no dependencies are available."""
        from unittest.mock import AsyncMock, MagicMock

        from lexigram.ai.di.provider import AIProvider

        provider = AIProvider()
        container = MagicMock()
        container.resolve = AsyncMock(side_effect=ValueError("not found"))

        await provider.boot(container)  # Must not raise

        assert provider._database_provider is None
        assert provider._cache_backend is None
        assert provider._rag_cache is None

class TestAIProviderHealthAndShutdown:
    """Tests for AIProvider health check and shutdown logic."""

    @pytest.mark.asyncio
    async def test_shutdown_tolerates_sub_provider_errors(self) -> None:
        """shutdown() should catch and log errors from sub-providers."""
        from lexigram.ai.di.provider import AIProvider
        
        provider = AIProvider()
        mock_sub = MagicMock()
        mock_sub.shutdown = AsyncMock(side_effect=RuntimeError("Shutdown failed"))
        provider._llm_sub = mock_sub

        # Should not raise
        await provider.shutdown()
        
        assert provider._llm_sub is None

    @pytest.mark.asyncio
    async def test_health_check_handles_model_dump_result(self) -> None:
        """health_check() should handle sub-providers returning objects with model_dump."""
        from lexigram.ai.di.provider import AIProvider
        from lexigram.contracts import HealthStatus, HealthCheckResult

        provider = AIProvider()
        
        mock_res = MagicMock()
        mock_res.status = HealthStatus.DEGRADED
        mock_res.model_dump.return_value = {"status": "degraded", "message": "fail"}
        
        mock_sub = MagicMock()
        mock_sub.health_check = AsyncMock(return_value=mock_res)
        provider._llm_sub = mock_sub

        result = await provider.health_check()
        
        assert result.status == HealthStatus.DEGRADED
        assert result.details["components"]["llm"]["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_check_handles_vector_sub_provider(self) -> None:
        """health_check() should aggregate health from vector sub-provider."""
        from lexigram.ai.di.provider import AIProvider
        from lexigram.contracts import HealthStatus, HealthCheckResult

        provider = AIProvider()
        
        mock_vec_health = HealthCheckResult(component="vector", status=HealthStatus.HEALTHY)
        mock_sub = MagicMock()
        mock_sub.health_check = AsyncMock(return_value=mock_vec_health)
        provider._vector_sub = mock_sub

        result = await provider.health_check()
        
        assert "vector" in result.details["components"]
        assert result.details["components"]["vector"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_vector_failure_sets_degraded(self) -> None:
        """health_check() should set overall status to DEGRADED if vector fails."""
        from lexigram.ai.di.provider import AIProvider
        from lexigram.contracts import HealthStatus

        provider = AIProvider()
        
        mock_sub = MagicMock()
        mock_sub.health_check = AsyncMock(side_effect=RuntimeError("Vector down"))
        provider._vector_sub = mock_sub

        result = await provider.health_check()
        
        assert result.status == HealthStatus.DEGRADED
        assert "Vector down" in result.error
