"""Content generator — uses LLM client to generate content."""

from __future__ import annotations

from typing import Any


class ContentGenerator:
    """Generates content using an LLM client.

    Demonstrates how to use an LLM client with retry logic
    and configurable styles.
    """

    def __init__(
        self,
        llm_client: Any,
        default_style: str = "professional",
        max_retries: int = 3,
    ) -> None:
        self._client = llm_client
        self._style = default_style
        self._max_retries = max_retries

    async def generate(
        self,
        topic: str,
        style: str | None = None,
    ) -> dict[str, Any]:
        """Generate content about a topic.

        Args:
            topic: The topic to generate content about.
            style: Optional style override (e.g. "casual", "technical").

        Returns:
            Dict with generated content and metadata.
        """
        used_style = style or self._style
        prompt = f"Write a {used_style} description about: {topic}"

        for attempt in range(self._max_retries):
            try:
                content = await self._client.complete(prompt)
                return {
                    "content": content,
                    "topic": topic,
                    "style": used_style,
                    "attempts": attempt + 1,
                }
            except Exception:
                if attempt == self._max_retries - 1:
                    raise
        return {"error": "Max retries exceeded"}

    async def generate_variations(
        self,
        topic: str,
        count: int = 3,
    ) -> list[dict[str, Any]]:
        """Generate multiple variations of content about a topic."""
        variations = []
        for i in range(count):
            result = await self.generate(
                topic,
                style=["professional", "casual", "technical"][i % 3],
            )
            variations.append(result)
        return variations
