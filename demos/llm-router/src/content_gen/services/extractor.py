"""Product extractor — structured extraction from LLM responses."""

from __future__ import annotations

from typing import Any

from lexigram.serialization import loads as json_loads


class ProductExtractor:
    """Extracts structured product data from text using an LLM client.

    Demonstrates structured extraction patterns with LLM clients.
    """

    def __init__(self, llm_client: Any) -> None:
        self._client = llm_client

    async def extract_product(self, description: str) -> dict[str, Any]:
        """Extract product information from a description.

        Args:
            description: Free-text product description.

        Returns:
            Dict with extracted product fields.
        """
        prompt = (
            f"Extract product information from this description as JSON: {description}\n"
            "Return only a JSON object with fields: name, price, category, features (list)"
        )

        response = await self._client.complete(prompt)

        try:
            return json_loads(response)
        except Exception:
            return {
                "name": "Unknown",
                "price": 0,
                "category": "Unknown",
                "features": [],
                "raw_response": response,
            }

    async def extract_many(
        self,
        descriptions: list[str],
    ) -> list[dict[str, Any]]:
        """Extract product info from multiple descriptions."""
        results = []
        for desc in descriptions:
            result = await self.extract_product(desc)
            results.append(result)
        return results
