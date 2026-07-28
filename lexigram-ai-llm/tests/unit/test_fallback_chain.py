"""Unit tests for FallbackChain."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.llm.routing.fallback import FallbackAttempt, FallbackChain


def _make_registry(
    models: list[dict] | None = None,
    client_error: Exception | None = None,
) -> MagicMock:
    """Build a mock ProviderRegistry."""
    registry = MagicMock()

    if models is None:
        models = []

    model_map: dict[str, MagicMock] = {}
    for m in models:
        mock_model = MagicMock()
        mock_model.model_id = m["model_id"]
        mock_model.provider = m["provider"]
        model_map[m["model_id"]] = mock_model

    registry.list_models.return_value = list(model_map.values())
    registry.get_model_info.side_effect = lambda mid: model_map.get(mid)

    async def _get_client(provider: str) -> MagicMock | None:
        if client_error:
            raise client_error
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "response"
        mock_client.complete = AsyncMock(return_value=mock_response)
        return mock_client

    registry.get_client = AsyncMock(side_effect=_get_client)
    return registry


class TestFallbackAttempt:
    def test_defaults(self) -> None:
        a = FallbackAttempt(model_id="gpt-4", provider="openai", success=True)
        assert a.success is True
        assert a.error is None
        assert a.fallback_reason is None


class TestFallbackChain:
    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        registry = _make_registry(
            models=[{"model_id": "gpt-4", "provider": "openai"}],
        )
        chain = FallbackChain(registry=registry)
        result = await chain.execute(
            [{"role": "user", "content": "hello"}],
            model_ids=["gpt-4"],
        )
        assert result.is_ok()
        assert chain.get_success_model() == "gpt-4"

    @pytest.mark.asyncio
    async def test_execute_no_models(self) -> None:
        registry = _make_registry(models=[])
        chain = FallbackChain(registry=registry)
        result = await chain.execute(
            [{"role": "user", "content": "hi"}],
            model_ids=[],
        )
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_execute_model_not_found(self) -> None:
        registry = _make_registry(models=[])
        chain = FallbackChain(registry=registry)
        result = await chain.execute(
            [{"role": "user", "content": "hi"}],
            model_ids=["nonexistent"],
        )
        assert result.is_err()
        assert chain.get_success_model() is None
        attempts = chain.get_attempt_details()
        assert len(attempts) == 1
        assert attempts[0].success is False

    @pytest.mark.asyncio
    async def test_execute_provider_unavailable(self) -> None:
        registry = _make_registry(
            models=[{"model_id": "gpt-4", "provider": "openai"}],
        )
        registry.get_client = AsyncMock(return_value=None)
        chain = FallbackChain(registry=registry)
        result = await chain.execute(
            [{"role": "user", "content": "hi"}],
            model_ids=["gpt-4"],
        )
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_execute_client_throws(self) -> None:
        registry = _make_registry(
            models=[
                {"model_id": "gpt-4", "provider": "openai"},
                {"model_id": "claude", "provider": "anthropic"},
            ],
        )
        # First client raises, second succeeds
        call_count = 0

        async def mock_get_client(provider: str) -> MagicMock:
            nonlocal call_count
            call_count += 1
            client = MagicMock()
            if call_count == 1:
                client.complete = AsyncMock(side_effect=RuntimeError("timeout"))
            else:
                resp = MagicMock()
                resp.content = "ok"
                client.complete = AsyncMock(return_value=resp)
            return client

        registry.get_client = AsyncMock(side_effect=mock_get_client)
        chain = FallbackChain(registry=registry)
        result = await chain.execute(
            [{"role": "user", "content": "hi"}],
            model_ids=["gpt-4", "claude"],
        )
        assert result.is_ok()
        assert chain.get_success_model() == "claude"

    @pytest.mark.asyncio
    async def test_max_attempts_limits_retries(self) -> None:
        models = [
            {"model_id": f"m{i}", "provider": "p"} for i in range(5)
        ]
        registry = _make_registry(models=models)
        chain = FallbackChain(registry=registry, max_retries=2)
        result = await chain.execute(
            [{"role": "user", "content": "hi"}],
            model_ids=[m["model_id"] for m in models],
        )
        # max_retries=2 ⇒ only 2 models tried
        assert result.is_ok()
        assert len(chain.get_attempt_details()) <= 2
