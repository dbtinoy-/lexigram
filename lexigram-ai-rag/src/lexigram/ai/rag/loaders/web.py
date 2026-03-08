"""Web document loader for RAG."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from lexigram.ai.rag.chunking.types import Chunk
from lexigram.ai.rag.types import RAGError
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class WebScraperLoader:
    """Scrape a web page and extract its text content.

    Uses ``ResilientHTTPClient`` (from ``lexigram-ai-llm``) for HTTP and
    BeautifulSoup for HTML parsing.

    Requires: beautifulsoup4
    Install: pip install lexigram-ai-rag[web]
    """

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        follow_links: bool = False,
        max_links: int = 5,
        user_agent: str = "Lexigram-RAG/1.0",
    ) -> None:
        """Initialize web scraper loader.

        Args:
            timeout: HTTP request timeout in seconds.
            follow_links: Whether to also scrape links found on the page.
            max_links: Maximum number of links to follow when
                ``follow_links=True``.
            user_agent: User-Agent header sent with requests.
        """
        self.timeout = timeout
        self.follow_links = follow_links
        self.max_links = max_links
        self.user_agent = user_agent

    async def load(self, source: str | Path) -> list[Chunk]:
        """Scrape a URL and return its text content as chunks.

        Args:
            source: URL to scrape (must start with ``http://`` or
                ``https://``).

        Returns:
            List of chunks (one per page when following links).

        Raises:
            ImportError: If beautifulsoup4 is not installed.
            RAGError: If the page cannot be fetched or parsed.
        """
        try:
            try:
                from bs4 import BeautifulSoup  # type: ignore[import-not-found]
            except ImportError as e:
                msg = "WebScraperLoader requires 'beautifulsoup4'. Install with: pip install beautifulsoup4"
                raise ImportError(msg) from e

            url = str(source)
            headers = {"User-Agent": self.user_agent}

            async def _fetch_and_parse(page_url: str) -> tuple[str, list[str]]:
                """Return (text_content, list_of_links)."""
                try:
                    import aiohttp
                except ImportError as _e:
                    msg = "WebScraperLoader requires 'aiohttp'. Install with: pip install aiohttp"
                    raise ImportError(msg) from _e
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as _session:
                    async with _session.get(page_url, headers=headers) as _resp:
                        html = await _resp.text()

                def _parse() -> Any:
                    soup = BeautifulSoup(html, "html.parser")
                    for tag in soup(["script", "style", "nav", "footer"]):
                        tag.decompose()
                    text = soup.get_text(separator="\n", strip=True)
                    links: list[str] = []
                    if self.follow_links:
                        for a_tag in soup.find_all("a", href=True):
                            href = str(a_tag["href"])
                            if href.startswith("http"):
                                links.append(href)
                    return text, links[: self.max_links]

                return await asyncio.to_thread(_parse)

            chunks: list[Chunk] = []
            text, links = await _fetch_and_parse(url)
            chunks.append(
                Chunk(
                    text=text,
                    source=url,
                    chunk_index=0,
                    metadata={"source": url, "type": "web"},
                )
            )

            if self.follow_links:
                for link_idx, link_url in enumerate(links, start=1):
                    try:
                        link_text, _ = await _fetch_and_parse(link_url)
                        chunks.append(
                            Chunk(
                                text=link_text,
                                source=link_url,
                                chunk_index=link_idx,
                                metadata={
                                    "source": link_url,
                                    "type": "web",
                                    "parent": url,
                                },
                            )
                        )
                    except Exception as e:  # noqa: BLE001 — broadened intentionally; individual link failures are non-fatal
                        logger.warning("link_fetch_failed", url=link_url, error=str(e))

            return chunks

        except (ImportError, RAGError):
            raise
        except Exception as e:
            msg = f"Failed to scrape {source}: {e}"
            raise RAGError(msg) from e


__all__ = ["WebScraperLoader"]
