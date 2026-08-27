"""Content API — HTTP surface for content generation.

Controllers are thin: they validate input, call a service, and
return a response dict.  No business logic lives here.

Convention followed: **Controller pattern** — each handler resolves its
dependencies from the container and returns domain ``Result`` values.
The framework's result bridge serializes them.

Exposes the content generator over HTTP:

- ``POST /api/content/generate``   — generate content about a topic
- ``POST /api/content/extract``    — extract product info from description
- ``GET /api/content/health``      — health check
"""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get, post


class ContentApiController(Controller):
    """HTTP surface for content generation.

    Delegates to services for business logic.  Returns dicts that
    the framework serialises to JSON.
    """

    prefix = "/api/content"

    def __init__(self, generator: object = None, extractor: object = None) -> None:
        self._generator = generator
        self._extractor = extractor

    @post("/generate")
    async def generate(self, body: dict[str, Any]) -> dict[str, Any]:
        """Generate content about a topic.

        Body: ``{"topic": "AI assistants", "style": "casual"}``
        """
        topic = body.get("topic", "")
        if not topic:
            return {"error": "Topic is required"}

        style = body.get("style")
        return await self._generator.generate(topic, style=style)

    @post("/variations")
    async def generate_variations(self, body: dict[str, Any]) -> dict[str, Any]:
        """Generate multiple variations of content about a topic.

        Body: ``{"topic": "AI assistants", "count": 3}``
        """
        topic = body.get("topic", "")
        if not topic:
            return {"error": "Topic is required"}

        count = body.get("count", 3)
        variations = await self._generator.generate_variations(topic, count=count)
        return {"topic": topic, "variations": variations}

    @post("/extract")
    async def extract_product(self, body: dict[str, Any]) -> dict[str, Any]:
        """Extract product information from a description.

        Body: ``{"description": "A wireless mouse with ergonomic design"}`
        """
        description = body.get("description", "")
        if not description:
            return {"error": "Description is required"}

        result = await self._extractor.extract_product(description)
        return {"product": result}

    @get("/health")
    async def health(self) -> dict[str, Any]:
        """Health check endpoint."""
        return {"status": "ok", "service": "content_gen"}


__all__ = ["ContentApiController"]
