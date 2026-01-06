"""Pricing data sources for LLM models.

This module provides abstraction for different pricing data sources with a clear
hierarchy: JSON files → API endpoints → Static fallback.

Example:
    >>> from lexigram.ai.llm.pricing_sources import JSONFilePricingSource
    >>>
    >>> source = JSONFilePricingSource(Path("pricing.json"))
    >>> pricing = await source.get_pricing("gpt-4-turbo")

"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from pathlib import Path
from typing import Any

from lexigram.ai.llm.http.client import ResilientHTTPClient
from lexigram.ai.llm.pricing.types import ModelPricing
from lexigram.logging import (
    get_logger,
)
from lexigram.serialization import loads

logger = get_logger(__name__)


class AbstractPricingSource(ABC):
    """Abstract base class for pricing data sources.

    All pricing sources must implement get_pricing() to return ModelPricing
    for a given model name, or None if not found.

    """

    @abstractmethod
    async def get_pricing(self, model: str) -> ModelPricing | None:
        """Get pricing for a specific model.

        Args:
            model: Model identifier (e.g., "gpt-4-turbo").

        Returns:
            ModelPricing if found, None otherwise.

        """

    @abstractmethod
    async def get_all_pricing(self) -> dict[str, ModelPricing]:
        """Get all available pricing data.

        Returns:
            Dictionary mapping model names to pricing.

        """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Get the name of this pricing source.

        Returns:
            Human-readable source name.

        """


class JSONFilePricingSource(AbstractPricingSource):
    """Pricing source from local JSON file.

    This is the fastest and most reliable source as it doesn't require
    network calls and works offline.

    Attributes:
        file_path: Path to JSON pricing file.
        cache: In-memory cache of loaded pricing.

    Example:
        >>> source = JSONFilePricingSource(Path("custom_pricing.json"))
        >>> pricing = await source.get_pricing("gpt-4-turbo")

    """

    def __init__(self, file_path: Path):
        """Initialize JSON file pricing source.

        Args:
            file_path: Path to JSON file containing pricing data.

        """
        self.file_path = file_path
        self._cache: dict[str, ModelPricing] | None = None

    async def _load_cache(self) -> dict[str, ModelPricing]:
        """Load pricing data from JSON file.

        Returns:
            Dictionary of model name to pricing.

        """
        if self._cache is not None:
            return self._cache

        exists = await asyncio.to_thread(self.file_path.exists)
        if not exists:
            logger.warning("JSON pricing file not found: %s", self.file_path)
            return {}

        try:

            def _read_json() -> Any:
                with open(self.file_path, "rb") as f:
                    return f.read()

            content = await asyncio.to_thread(_read_json)
            data = loads(content)

            pricing = {}

            # Load regular models
            for model_name, model_data in data.get("models", {}).items():
                pricing[model_name.lower()] = ModelPricing(
                    model=model_name,
                    prompt_per_1m=model_data.get("prompt_per_1m", 1.0),
                    completion_per_1m=model_data.get("completion_per_1m", 2.0),
                    provider=model_data.get("provider", "unknown"),
                    source=f"json:{self.file_path.name}",
                )
        except (OSError, ValueError, TypeError) as e:
            logger.warning("Failed to load pricing from JSON %s: %s", self.file_path, e)
            return {}
        else:
            self._cache = pricing
            logger.info(
                "Loaded pricing for %d models from %s",
                len(pricing),
                self.file_path.name,
            )
            return pricing

    async def get_pricing(self, model: str) -> ModelPricing | None:
        """Get pricing for a specific model.

        Args:
            model: Model identifier.

        Returns:
            ModelPricing if found, None otherwise.

        """
        cache = await self._load_cache()
        return cache.get(model.lower())

    async def get_all_pricing(self) -> dict[str, ModelPricing]:
        """Get all pricing data.

        Returns:
            All pricing data from JSON file.

        """
        return await self._load_cache()

    @property
    def source_name(self) -> str:
        """Get source name."""
        return f"JSON File ({self.file_path.name})"

    def invalidate_cache(self) -> None:
        """Clear cached pricing data to force reload."""
        self._cache = None


class APIPricingSource(AbstractPricingSource):
    """Pricing source from HTTP API endpoint.

    Fetches pricing data from a remote API. Useful for getting the latest
    pricing updates, but requires network connectivity.

    Attributes:
        endpoint: API endpoint URL.
        timeout: Request timeout in seconds.

    Example:
        >>> source = APIPricingSource(
        ...     "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
        ... )
        >>> pricing = await source.get_pricing("gpt-4")

    """

    def __init__(self, endpoint: str, timeout: float = 10.0):
        """Initialize API pricing source.

        Args:
            endpoint: URL to fetch pricing from.
            timeout: Request timeout in seconds (default: 10).

        """
        self.endpoint = endpoint
        self.timeout = timeout
        self._cache: dict[str, ModelPricing] | None = None

    async def _fetch_pricing(self) -> dict[str, ModelPricing]:
        """Fetch pricing from API endpoint.

        Returns:
            Dictionary of model pricing.

        """
        if self._cache is not None:
            return self._cache

        try:
            async with ResilientHTTPClient(
                timeout=self.timeout,
                name="pricing-api",
            ) as client:
                response = await client.get(self.endpoint)
                response.raise_for_status()

                data: Any = response.json
                if asyncio.iscoroutine(data):
                    data = await data
                pricing = {}

                for model_name, model_data in (data or {}).items():
                    # Extract pricing (LiteLLM format stores per-token, convert to per-1M)
                    input_cost = model_data.get("input_cost_per_token", 0) * 1_000_000
                    output_cost = model_data.get("output_cost_per_token", 0) * 1_000_000

                    if input_cost > 0:
                        # Infer provider from model name
                        provider = self._infer_provider(model_name)

                        pricing[model_name.lower()] = ModelPricing(
                            model=model_name,
                            prompt_per_1m=input_cost,
                            completion_per_1m=output_cost,
                            provider=provider,
                            source=f"api:{self.endpoint}",
                        )

                self._cache = pricing
                logger.info(
                    "Fetched pricing for %d models from %s",
                    len(pricing),
                    self.endpoint,
                )
                return pricing

        except (OSError, ValueError, TypeError) as e:
            logger.warning("Failed to fetch pricing from %s: %s", self.endpoint, e)
            return {}

    def _infer_provider(self, model_name: str) -> str:
        """Infer provider from model name.

        Args:
            model_name: Model identifier.

        Returns:
            Provider name.

        """
        model_lower = model_name.lower()
        if "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        if "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        if "gemini" in model_lower:
            return "google"
        if "mistral" in model_lower or "mixtral" in model_lower:
            return "mistral"
        if "command" in model_lower or "cohere" in model_lower:
            return "cohere"
        if "llama" in model_lower and "groq" not in model_lower:
            return "meta"
        return "unknown"

    async def get_pricing(self, model: str) -> ModelPricing | None:
        """Get pricing for a specific model.

        Args:
            model: Model identifier.

        Returns:
            ModelPricing if found, None otherwise.

        """
        cache = await self._fetch_pricing()
        return cache.get(model.lower())

    async def get_all_pricing(self) -> dict[str, ModelPricing]:
        """Get all pricing data.

        Returns:
            All pricing data from API.

        """
        return await self._fetch_pricing()

    @property
    def source_name(self) -> str:
        """Get source name."""
        return f"API ({self.endpoint})"

    def invalidate_cache(self) -> None:
        """Clear cached pricing data to force refresh."""
        self._cache = None


class StaticPricingSource(AbstractPricingSource):
    """Pricing source from static dictionary.

    Hardcoded pricing data as a fallback when other sources are unavailable.
    Useful for custom internal models or as ultimate fallback.

    Attributes:
        pricing_map: Dictionary of model name to pricing.

    Example:
        >>> source = StaticPricingSource({
        ...     "my-model": ModelPricing(
        ...         model="my-model",
        ...         prompt_per_1m=5.0,
        ...         completion_per_1m=10.0,
        ...         provider="custom"
        ...     )
        ... })

    """

    def __init__(self, pricing_map: dict[str, ModelPricing]):
        """Initialize static pricing source.

        Args:
            pricing_map: Dictionary mapping model names to pricing.

        """
        # Normalize keys to lowercase
        self.pricing_map = {k.lower(): v for k, v in pricing_map.items()}

    async def get_pricing(self, model: str) -> ModelPricing | None:
        """Get pricing for a specific model.

        Args:
            model: Model identifier.

        Returns:
            ModelPricing if found, None otherwise.

        """
        return self.pricing_map.get(model.lower())

    async def get_all_pricing(self) -> dict[str, ModelPricing]:
        """Get all pricing data.

        Returns:
            All static pricing data.

        """
        return self.pricing_map.copy()

    @property
    def source_name(self) -> str:
        """Get source name."""
        return f"Static ({len(self.pricing_map)} models)"
