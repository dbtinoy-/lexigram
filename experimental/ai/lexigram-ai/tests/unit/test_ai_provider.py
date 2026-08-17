"""Tests for lexigram.ai.provider module (sub-provider composition)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.config import (
    AIConfig,
    GovernanceConfig,
    VectorConfig,
)
from lexigram.ai.config import (
    ClientConfig as LLMConfig,
)
from lexigram.ai.di.provider import AIProvider


class TestAIProviderInitialization:
    """Tests for AIProvider constructor."""

    def test_default_initialization(self):
        """Default initialization sets correct state."""
        provider = AIProvider()

        assert provider.name == "ai"
        assert isinstance(provider.intelligence_config, AIConfig)
        assert provider.database_provider is None
        assert provider.cache_backend is None

        # Sub-provider slots are empty
        assert provider._llm_sub is None
        assert provider._vector_sub is None
        assert provider._rag_sub is None

    def test_initialization_with_config(self):
        """Custom name and config are stored correctly."""
        config = AIConfig()
        provider = AIProvider(
            name="custom-ai",
            config=config,
        )

        assert provider.name == "custom-ai"
        assert provider.intelligence_config is config

    def test_config_overrides_applied(self):
        """llm_config / vector_config kwargs override base config."""
        base = AIConfig()
        llm = LLMConfig(provider="openai", model="gpt-4")
        vec = VectorConfig(backend="chroma", collection_name="test")

        provider = AIProvider(
            config=base,
            llm_config=llm,
            vector_config=vec,
        )

        assert provider.intelligence_config.llm == llm
        assert provider.intelligence_config.vector == vec


class TestAIProviderRegister:
    """Tests for AIProvider.register() sub-provider delegation."""

    @pytest.fixture
    def mock_container(self):
        container = MagicMock()
        container.singleton = MagicMock()
        container.resolve = AsyncMock(return_value=None)
        container.resolve_optional = AsyncMock(return_value=None)
        return container

    @pytest.mark.asyncio
    async def test_register_always_registers_monitoring(self, mock_container):
        """Monitoring singletons are always registered regardless of config."""
        from lexigram.ai.observability import AIHealthMonitor
        from lexigram.ai.observability.metrics import AIMetrics
        from lexigram.ai.observability.tracing import AITracer

        provider = AIProvider()
        await provider.register(mock_container)

        registered_types = [
            call.args[0] if call.args else None
            for call in mock_container.singleton.call_args_list
        ]
        assert AIHealthMonitor in registered_types
        assert AIMetrics in registered_types
        assert AITracer in registered_types

    @pytest.mark.asyncio
    async def test_register_no_config_creates_no_sub_providers(self, mock_container):
        """With no LLM/vector/RAG/ML config, no sub-providers are instantiated."""
        provider = AIProvider()
        await provider.register(mock_container)

        assert provider._llm_sub is None
        assert provider._vector_sub is None
        assert provider._rag_sub is None

    @pytest.mark.asyncio
    async def test_register_delegates_to_llm_provider(self, mock_container):
        """LLM config causes LLMProvider to be instantiated and registered."""
        config = AIConfig(llm=LLMConfig(provider="openai", model="gpt-4"))
        provider = AIProvider()
        # Simulate orchestrator setting the config
        provider.config = config

        await provider.register(mock_container)

        # Verify LLMProvider was instantiated and stored
        assert provider._llm_sub is not None

        # Verify config was registered so sub-providers can access it
        registered_types = [
            call.args[0] if call.args else None
            for call in mock_container.singleton.call_args_list
        ]
        assert AIConfig in registered_types

    @pytest.mark.asyncio
    async def test_register_delegates_to_vector_provider(self, mock_container):
        """Vector config causes VectorProvider to be instantiated and registered."""
        config = AIConfig(
            vector=VectorConfig(backend="chroma", collection_name="test")
        )
        provider = AIProvider()
        # Simulate orchestrator setting the config
        provider.config = config

        await provider.register(mock_container)

        # Verify VectorProvider was instantiated and stored
        assert provider._vector_sub is not None

        # Verify config was registered so sub-providers can access it
        registered_types = [
            call.args[0] if call.args else None
            for call in mock_container.singleton.call_args_list
        ]
        assert AIConfig in registered_types

    @pytest.mark.asyncio
    async def test_register_delegates_to_rag_provider(self, mock_container):
        """RAG config causes RAGProvider to be instantiated and registered."""
        from lexigram.ai.rag.config import RAGConfig

        config = AIConfig(rag=RAGConfig())
        provider = AIProvider()
        # Simulate orchestrator setting the config
        provider.config = config

        await provider.register(mock_container)

        # Verify RAGProvider was instantiated and stored
        assert provider._rag_sub is not None

        # Verify config was registered so sub-providers can access it
        registered_types = [
            call.args[0] if call.args else None
            for call in mock_container.singleton.call_args_list
        ]
        assert AIConfig in registered_types

    @pytest.mark.asyncio
    async def test_register_does_not_register_governance_services(
        self, mock_container
    ):
        """Governance registration is owned by GovernanceProvider, not AIProvider."""
        from unittest.mock import patch

        from lexigram.ai.governance.audit import AIAuditStore
        from lexigram.ai.governance.services.manager import AIGovernanceManager

        provider = AIProvider()
        provider.config = AIConfig(governance=GovernanceConfig(enabled=True))

        # Suppress entry-point discovery so only AIProvider's own code runs.
        with patch("importlib.metadata.entry_points", return_value=[]):
            await provider.register(mock_container)

        registered_types = [
            call.args[0] if call.args else None
            for call in mock_container.singleton.call_args_list
        ]
        assert AIGovernanceManager not in registered_types
        assert AIAuditStore not in registered_types


class TestAIProviderBoot:
    """Tests for AIProvider.boot() — AIProvider-specific async I/O only."""

    @pytest.fixture
    def mock_container(self):
        container = MagicMock()
        container.resolve = AsyncMock(side_effect=ValueError("no EventBusProtocol"))
        return container

    @pytest.mark.asyncio
    async def test_boot_no_config_does_nothing(self, mock_container):
        """boot() with no config leaves all AIProvider-specific references None."""
        provider = AIProvider()
        await provider.boot(mock_container)

        assert provider._rag_cache is None


class TestAIProviderShutdown:
    """Tests for AIProvider.shutdown()."""

    @pytest.mark.asyncio
    async def test_shutdown_calls_sub_provider_shutdown(self):
        """shutdown() propagates to all instantiated sub-providers."""
        provider = AIProvider()

        mock_llm_sub = MagicMock()
        mock_llm_sub.shutdown = AsyncMock()
        mock_vector_sub = MagicMock()
        mock_vector_sub.shutdown = AsyncMock()

        provider._llm_sub = mock_llm_sub
        provider._vector_sub = mock_vector_sub

        await provider.shutdown()

        mock_llm_sub.shutdown.assert_called_once()
        mock_vector_sub.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_clears_all_references(self):
        """After shutdown, all sub-provider and service references are None."""
        provider = AIProvider()

        provider._llm_sub = MagicMock()
        provider._llm_sub.shutdown = AsyncMock()
        provider._vector_sub = MagicMock()
        provider._vector_sub.shutdown = AsyncMock()

        await provider.shutdown()

        assert provider._llm_sub is None
        assert provider._vector_sub is None
        assert provider._rag_sub is None
        assert provider._rag_cache is None

    @pytest.mark.asyncio
    async def test_shutdown_no_services_is_safe(self):
        """shutdown() with no sub-providers or services completes without error."""
        provider = AIProvider()
        await provider.shutdown()  # Must not raise


class TestAIProviderHealthCheck:
    """Tests for AIProvider.health_check() delegation."""

    @pytest.mark.asyncio
    async def test_health_check_no_services_returns_healthy(self):
        """No sub-providers → HEALTHY with empty components."""
        from lexigram.contracts.core import HealthStatus

        provider = AIProvider()
        result = await provider.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.details["components"] == {}

    @pytest.mark.asyncio
    async def test_health_check_delegates_to_llm_sub(self):
        """LLM health is delegated to _llm_sub.health_check()."""
        from lexigram.contracts.core import HealthStatus

        provider = AIProvider()
        mock_llm_sub = MagicMock()
        mock_llm_sub.health_check = AsyncMock(
            return_value={"status": "healthy", "provider": "openai"}
        )
        provider._llm_sub = mock_llm_sub

        result = await provider.health_check()

        mock_llm_sub.health_check.assert_called_once()
        assert "llm" in result.details["components"]
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_delegates_to_vector_sub(self):
        """Vector health is delegated to _vector_sub.health_check()."""
        from lexigram.contracts.core import HealthCheckResult, HealthStatus

        provider = AIProvider()
        mock_vector_sub = MagicMock()
        mock_vector_sub.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="vector",
                status=HealthStatus.HEALTHY,
                details={"vectors": 100},
            )
        )
        provider._vector_sub = mock_vector_sub

        result = await provider.health_check()

        mock_vector_sub.health_check.assert_called_once()
        assert "vector" in result.details["components"]
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_degraded_when_llm_sub_unhealthy(self):
        """DEGRADED status propagates when LLM sub-provider reports unhealthy."""
        from lexigram.contracts.core import HealthStatus

        provider = AIProvider()
        mock_llm_sub = MagicMock()
        mock_llm_sub.health_check = AsyncMock(
            return_value={"status": "unhealthy", "error": "timeout"}
        )
        provider._llm_sub = mock_llm_sub

        result = await provider.health_check()

        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_health_check_degraded_on_llm_sub_exception(self):
        """RuntimeError from LLM sub-provider sets DEGRADED and records error."""
        from lexigram.contracts.core import HealthStatus

        provider = AIProvider()
        mock_llm_sub = MagicMock()
        mock_llm_sub.health_check = AsyncMock(
            side_effect=RuntimeError("Connection refused")
        )
        provider._llm_sub = mock_llm_sub

        result = await provider.health_check()

        assert result.status == HealthStatus.DEGRADED
        assert result.details["components"]["llm"]["status"] == "unhealthy"
        assert "Connection refused" in result.details["components"]["llm"]["error"]


class TestFactoriesDirect:
    """Tests for factory functions in lexigram.ai.di.factories."""

    @pytest.mark.asyncio
    async def test_create_vector_store_without_infra_store_returns_mock(self):
        """create_vector_store falls back to MockVectorStore when no infra store is given."""
        from lexigram.vector.di.factories import create_vector_store
        from lexigram.vector.testing.mocks import MockVectorStore

        config = VectorConfig(backend="qdrant", collection_name="test")

        result = await create_vector_store(config)

        assert isinstance(result, MockVectorStore)

    @pytest.mark.asyncio
    async def test_create_vector_store_with_infra_store_returns_adapter(self):
        """create_vector_store wraps an infra store in VectorStoreAdapter."""
        from unittest.mock import MagicMock

        from lexigram.vector.adapters.vector_store import VectorStoreAdapter
        from lexigram.vector.di.factories import create_vector_store

        config = VectorConfig(backend="qdrant", collection_name="test", default_dimension=3)
        infra_store = MagicMock()

        result = await create_vector_store(config, infra_store=infra_store)

        assert isinstance(result, VectorStoreAdapter)
