"""WebToolkit - web browsing and search skills."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from lexigram.ai.skills.base import AbstractSkill
from lexigram.ai.skills.exceptions import SkillExecutionError
from lexigram.ai.skills.toolkits.toolkit import Toolkit
from lexigram.contracts.ai.skills import (
    SkillDefinition,
    SkillError,
    SkillProtocol,
    SkillResult,
)
from lexigram.result import Err, Ok, Result
from lexigram.serialization import JSONDecodeError
from lexigram.serialization import loads as json_loads

if TYPE_CHECKING:
    from collections.abc import Awaitable

    class _HTTPClientProtocol:
        """Minimal protocol for HTTP client."""

        def request(
            self,
            method: str,
            url: str,
            **kwargs: Any,
        ) -> Awaitable[dict[str, Any]]:
            """Make an HTTP request."""


class WebSearchSkill(AbstractSkill):
    """Search the web using an HTTP client."""

    def __init__(self, http_client: _HTTPClientProtocol) -> None:
        """Initialise with HTTP client.

        Args:
            http_client: HTTP client implementing request method.
        """
        self._client = http_client

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition."""
        return SkillDefinition(
            name="web_search",
            description="Search the web and return ranked results.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string.",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return.",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
            category="web",
            permissions=["web.search"],
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Execute the web search."""
        query: str = kwargs.get("query", "")
        num_results: int = kwargs.get("num_results", 10)

        if not query:
            return Err(SkillExecutionError("Search query is required."))

        try:
            response = await self._client.request(
                "GET",
                f"https://api.example.com/search?q={query}&num={num_results}",
            )

            if response.get("status") != 200:
                return Err(
                    SkillExecutionError(
                        f"Search API returned status {response.get('status')}"
                    )
                )

            body = response.get("body", "{}")
            data = json_loads(body) if isinstance(body, str) else body

            results = data.get("results", [])
        except JSONDecodeError as exc:
            return Err(SkillExecutionError(f"Failed to parse search results: {exc}"))
        except Exception as exc:
            return Err(SkillExecutionError(f"Web search failed: {exc}"))

        return Ok(
            SkillResult(
                skill_name="web_search",
                success=True,
                output={"results": results, "query": query},
            )
        )


class WebBrowseSkill(AbstractSkill):
    """Browse a web page and extract its content."""

    def __init__(self, http_client: _HTTPClientProtocol) -> None:
        """Initialise with HTTP client.

        Args:
            http_client: HTTP client implementing request method.
        """
        self._client = http_client

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition."""
        return SkillDefinition(
            name="web_browse",
            description="Fetch and extract content from a web page.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the page to fetch.",
                    },
                    "extract": {
                        "type": "string",
                        "description": "What to extract: 'text', 'html', or 'metadata'.",
                        "default": "text",
                    },
                },
                "required": ["url"],
            },
            category="web",
            permissions=["web.browse"],
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Execute the web browse."""
        url: str = kwargs.get("url", "")
        extract: str = kwargs.get("extract", "text")

        if not url:
            return Err(SkillExecutionError("URL is required."))

        try:
            response = await self._client.request("GET", url)

            if response.get("status") != 200:
                return Err(
                    SkillExecutionError(
                        f"Browse returned status {response.get('status')}"
                    )
                )

            body = response.get("body", "")

            if extract == "html":
                output = body
            elif extract == "metadata":
                output = {
                    "url": url,
                    "status": response.get("status"),
                }
            else:
                output = self._extract_text(body)

        except Exception as exc:
            return Err(SkillExecutionError(f"Web browse failed: {exc}"))

        return Ok(
            SkillResult(
                skill_name="web_browse",
                success=True,
                output={"url": url, "content": output},
            )
        )

    def _extract_text(self, html: str) -> str:
        """Extract plain text from HTML."""
        text = html
        for tag in ["<script>", "</script>", "<style>", "</style>"]:
            text = text.replace(tag, "")

        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


class WebToolkit(Toolkit):
    """Toolkit providing web browsing and search skills.

    Provides skills for searching the web and browsing web pages.
    """

    def __init__(self, http_client: _HTTPClientProtocol) -> None:
        """Initialise with HTTP client.

        Args:
            http_client: HTTP client implementing request method.
        """
        super().__init__(
            name="web",
            description="Web browsing and search toolkit",
        )
        self._client = http_client

    def _get_tools(self) -> tuple[SkillProtocol, ...]:
        """Return the web toolkit skills."""
        return (
            WebSearchSkill(self._client),
            WebBrowseSkill(self._client),
        )


__all__ = ["WebBrowseSkill", "WebSearchSkill", "WebToolkit"]
