"""Entity extractor — parses subject/predicate/object triples from text."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.memory.exceptions import FactExtractionError
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from lexigram.contracts.ai.memory import MemoryEntry

logger = get_logger(__name__)

# Simple pattern-based fallback triples  (subject, predicate, object_)
Triple = tuple[str, str, str]


class EntityExtractor:
    """Extracts structured subject/predicate/object triples from memory entries.

    When an LLM extract callable is injected, delegation occurs there.
    Otherwise a lightweight heuristic fallback is used, suitable for
    testing and environments without LLM access.
    """

    def __init__(
        self,
        extract_fn: Callable[[str], Awaitable[list[Triple]]] | None = None,
    ) -> None:
        """Initialise the extractor.

        Args:
            extract_fn: Async callable that returns triples from raw text.
                When *None*, a heuristic fallback is used.
        """
        self._extract_fn = extract_fn

    async def extract(self, entry: MemoryEntry) -> list[Triple]:
        """Extract triples from *entry.content*.

        Args:
            entry: Memory entry whose content to parse.

        Returns:
            List of (subject, predicate, object_) tuples.

        Raises:
            FactExtractionError: If the extraction callable raises.
        """
        if self._extract_fn:
            try:
                return await self._extract_fn(entry.content)
            except (RuntimeError, ValueError, TypeError) as exc:
                raise FactExtractionError(
                    f"Extraction failed for entry {entry.id}"
                ) from exc
        return self._heuristic_extract(entry)

    def _heuristic_extract(self, entry: MemoryEntry) -> list[Triple]:
        """Naive heuristic — extracts 'X is Y' and 'X has Y' patterns."""
        triples: list[Triple] = []
        content = entry.content
        for phrase in content.split("."):
            phrase = phrase.strip()
            for sep in (" is ", " are ", " has ", " have ", " was ", " were "):
                if sep in phrase:
                    parts = phrase.split(sep, 1)
                    if len(parts) == 2 and parts[0] and parts[1]:
                        subject = parts[0].strip().lower()
                        predicate = sep.strip()
                        object_ = parts[1].strip().lower()
                        if len(subject) <= 60 and len(object_) <= 120:
                            triples.append((subject, predicate, object_))
                    break
        return triples


# Avoid circular import for type hints

__all__ = ["EntityExtractor"]
