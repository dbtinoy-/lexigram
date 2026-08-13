"""Tests for PricingManager.get_pricing unknown-model handling."""

from __future__ import annotations

import pytest

from lexigram.ai.llm.pricing import ModelPricing, PricingManager
from lexigram.ai.llm.pricing.sources import AbstractPricingSource


class _FakeSource(AbstractPricingSource):
    """Pricing source double."""

    source_name = "fake"

    def __init__(self, data: dict[str, ModelPricing]) -> None:
        self._data = data

    async def get_pricing(self, model: str) -> ModelPricing | None:
        return self._data.get(model)

    async def get_all_pricing(self) -> dict[str, ModelPricing]:
        return dict(self._data)


class TestGetPricingUnknownModel:
    """Unknown models resolve to None and are never fabricated."""

    @pytest.mark.asyncio
    async def test_unknown_model_returns_none(self) -> None:
        manager = PricingManager(sources=[_FakeSource({})])

        result = await manager.get_pricing("gpt-4oo")

        assert result is None

    @pytest.mark.asyncio
    async def test_unknown_model_not_cached(self) -> None:
        manager = PricingManager(sources=[_FakeSource({})])
        await manager.get_pricing("gpt-4oo")

        assert await manager.cache.get("gpt-4oo") is None

    @pytest.mark.asyncio
    async def test_known_model_returned_and_cached(self) -> None:
        entry = ModelPricing(
            model="openai/gpt-4o",
            prompt_per_1m=2.5,
            completion_per_1m=10.0,
            provider="openai",
            source="fake",
        )
        manager = PricingManager(sources=[_FakeSource({"openai/gpt-4o": entry})])

        result = await manager.get_pricing("openai/gpt-4o")

        assert result is entry
        assert await manager.cache.get("openai/gpt-4o") is entry
