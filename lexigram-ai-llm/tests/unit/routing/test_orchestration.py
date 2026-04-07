"""Tests for the LLM orchestrator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.ai.models import ModelRequest
from lexigram.contracts.ai.providers import ModelCapability
from lexigram.ai.llm.routing.orchestrator import (
    LLMOrchestrator,
    NoSuitableModelError,
    OrchestratorError,
)
from lexigram.ai.llm.registry.core import ProviderRegistry
from lexigram.ai.llm.types import Completion, TokenUsage
from lexigram.result import Ok


class TestLLMOrchestrator:
    """Test suite for LLMOrchestrator."""

    @pytest.fixture
    def registry(self) -> ProviderRegistry:
        """Create a fresh registry."""
        return ProviderRegistry()

    @pytest.fixture
    def orchestrator(self, registry: ProviderRegistry) -> LLMOrchestrator:
        """Create an orchestrator with a registry."""
        return LLMOrchestrator(registry)

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock LLM client."""
        client = MagicMock()
        response = Completion(
            content="Generated response",
            model="gpt-4",
            usage=TokenUsage(
                prompt_tokens=60,
                completion_tokens=40,
                total_tokens=100,
            ),
        )
        client.complete = AsyncMock(return_value=Ok(response))
        return client

    @pytest.mark.asyncio
    async def test_execute_with_explicit_model(
        self,
        orchestrator: LLMOrchestrator,
        mock_client: MagicMock,
    ) -> None:
        """Test execution with explicitly specified model."""
        request = ModelRequest(
            model_id="gpt-4-turbo",
            prompt="What is 2+2?",
            extra_params={"client": mock_client},
        )

        result = await orchestrator.execute(request)

        assert result.is_ok()
        response = result.unwrap()
        assert response.content == "Generated response"
        mock_client.complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_with_capability_filter(
        self,
        orchestrator: LLMOrchestrator,
        mock_client: MagicMock,
    ) -> None:
        """Test execution with capability-based model selection."""
        request = ModelRequest(
            prompt="Generate image description",
            required_capabilities={ModelCapability.VISION},
            extra_params={"client": mock_client},
        )

        result = await orchestrator.execute(request)

        assert result.is_ok()
        response = result.unwrap()
        assert response.content == "Generated response"

    @pytest.mark.asyncio
    async def test_execute_no_suitable_model(
        self,
        orchestrator: LLMOrchestrator,
    ) -> None:
        """Test execution fails when no model matches requirements."""
        request = ModelRequest(
            model_id="nonexistent-model",
            prompt="Some prompt",
        )

        result = await orchestrator.execute(request)

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, NoSuitableModelError)

    @pytest.mark.asyncio
    async def test_execute_provider_unavailable(
        self,
        orchestrator: LLMOrchestrator,
        registry: ProviderRegistry,
        mock_client: MagicMock,
    ) -> None:
        """Test execution fails when provider is unavailable."""
        request = ModelRequest(
            prompt="Test",
            required_capabilities={ModelCapability.VISION},
            extra_params={"client": mock_client},
        )

        with pytest.raises(OrchestratorError):
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    registry,
                    "get_provider",
                    MagicMock(side_effect=KeyError("missing provider")),
                )
                await orchestrator.execute(request)

    @pytest.mark.asyncio
    async def test_execute_client_error(
        self,
        orchestrator: LLMOrchestrator,
    ) -> None:
        """Test execution handles client errors gracefully."""
        error_client = MagicMock()
        error_client.complete = AsyncMock(
            side_effect=RuntimeError("Provider API error")
        )

        request = ModelRequest(
            model_id="gpt-4",
            prompt="Test",
            extra_params={"client": error_client},
        )

        result = await orchestrator.execute(request)

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_select_model_explicit_id(
        self,
        orchestrator: LLMOrchestrator,
    ) -> None:
        """Test model selection with explicit model ID."""
        request = ModelRequest(
            model_id="gpt-3.5-turbo",
            prompt="Test",
        )

        model = orchestrator._select_model(request)

        assert model is not None
        assert model.model_id == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    async def test_select_model_by_capability(
        self,
        orchestrator: LLMOrchestrator,
    ) -> None:
        """Test model selection by capability."""
        request = ModelRequest(
            prompt="Generate image description",
            required_capabilities={ModelCapability.VISION},
        )

        model = orchestrator._select_model(request)

        assert model is not None
        assert model.provider == "openai"

    @pytest.mark.asyncio
    async def test_select_model_multiple_capabilities(
        self,
        orchestrator: LLMOrchestrator,
    ) -> None:
        """Test selecting model that supports multiple capabilities."""
        request = ModelRequest(
            prompt="Complex task",
            required_capabilities={ModelCapability.VISION, ModelCapability.FUNCTION_CALLING},
        )

        model = orchestrator._select_model(request)

        assert model is not None
        assert model.provider == "openai"
