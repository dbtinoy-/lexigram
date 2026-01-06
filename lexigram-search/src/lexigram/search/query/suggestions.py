"""Suggestion engine for typo-tolerant autocomplete and did-you-mean."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.search import SearchEngineProtocol

logger = get_logger(__name__)


@dataclass
class Suggestion:
    """A single suggestion result."""

    text: str
    score: float = 1.0
    frequency: int = 0
    type: str = "completion"  # "completion", "correction", "prediction"


@dataclass
class SuggestionResult:
    """Result from a suggestion query."""

    suggestions: list[Suggestion] = field(default_factory=list)
    query: str = ""
    did_you_mean: str | None = None


class SuggestionEngine:
    """Suggestion engine providing autocomplete and typo-tolerant suggestions.

    This engine provides:
    - Prefix-based autocomplete suggestions
    - Did-you-mean corrections for misspellings
    - Popular/search frequency-based suggestions

    Example::

        suggestion_engine = SuggestionEngine(
            search_engine=my_search_engine,
            index_name="products",
        )

        # Get autocomplete suggestions
        suggestions = await suggestion_engine.suggest("lap")

        # Get did-you-mean correction
        correction = await suggestion_engine.did_you_mean("laptap")
    """

    def __init__(
        self,
        search_engine: SearchEngineProtocol,
        index_name: str = "default",
        min_score: float = 0.5,
        max_suggestions: int = 10,
    ) -> None:
        """Initialize the suggestion engine.

        Args:
            search_engine: The search engine to use for suggestions.
            index_name: The index to search for suggestions.
            min_score: Minimum score threshold for suggestions.
            max_suggestions: Maximum number of suggestions to return.
        """
        self._engine = search_engine
        self._index_name = index_name
        self._min_score = min_score
        self._max_suggestions = max_suggestions

    async def suggest(
        self,
        prefix: str,
        field: str = "name",
        filters: dict[str, Any] | None = None,
    ) -> SuggestionResult:
        """Get autocomplete suggestions for a prefix.

        Args:
            prefix: The prefix to get suggestions for.
            field: The field to search for suggestions.
            filters: Optional filters to apply.

        Returns:
            SuggestionResult with matching suggestions.
        """
        if not prefix or len(prefix) < 2:
            return SuggestionResult(query=prefix)

        # Build a query that matches the prefix
        # Using wildcard for prefix matching
        query = f"{prefix}*"

        try:
            result = await self._engine.search(
                query=query,
                filters=filters,
                limit=self._max_suggestions,
            )

            suggestions = []
            for doc in result.documents:  # type: ignore[attr-defined]
                # Extract the suggestion text from the field
                text = doc.get(field, "")
                if text:
                    # Calculate a simple score based on length (shorter = better match)
                    score = 1.0 - (len(text) - len(prefix)) * 0.1
                    score = max(score, self._min_score)

                    suggestions.append(
                        Suggestion(
                            text=str(text),
                            score=score,
                            type="completion",
                        )
                    )

            return SuggestionResult(
                suggestions=suggestions,
                query=prefix,
            )

        except (OSError, ConnectionError, RuntimeError, ValueError) as e:
            logger.error(
                "suggestion_error",
                prefix=prefix,
                error=str(e),
            )
            return SuggestionResult(query=prefix)

    async def did_you_mean(
        self,
        query: str,
        max_variants: int = 3,
    ) -> SuggestionResult:
        """Get did-you-mean corrections for a query.

        Performs simple typo detection and suggests corrections.

        Args:
            query: The misspelled query.
            max_variants: Maximum number of correction variants to generate.

        Returns:
            SuggestionResult with correction suggestions.
        """
        if not query or len(query) < 3:
            return SuggestionResult(query=query)

        # Generate simple correction candidates
        corrections = self._generate_corrections(query, max_variants)

        # Try each correction and find one that returns results
        for correction in corrections:
            try:
                result = await self._engine.search(
                    query=correction,
                    limit=1,
                )

                if result.total > 0:  # type: ignore[attr-defined]
                    return SuggestionResult(
                        suggestions=[
                            Suggestion(
                                text=correction,
                                score=1.0,
                                type="correction",
                            )
                        ],
                        query=query,
                        did_you_mean=correction,
                    )
            except (OSError, ConnectionError, RuntimeError, ValueError) as e:
                logger.debug(
                    "correction_search_failed", correction=correction, error=str(e)
                )
                continue

        return SuggestionResult(query=query)

    def _generate_corrections(
        self,
        query: str,
        max_variants: int,
    ) -> list[str]:
        """Generate correction candidates for a query.

        Simple implementation that tries common typo patterns.

        Args:
            query: The original query.
            max_variants: Maximum number of variants to generate.

        Returns:
            List of correction candidates.
        """
        corrections: list[str] = []
        seen: set[str] = {query}

        # Try removing duplicate characters (e.g., "laptopp" -> "laptop")
        deduped = self._remove_duplicate_chars(query)
        if deduped not in seen and len(deduped) >= 3:
            corrections.append(deduped)
            seen.add(deduped)

        # Try common keyboard typo corrections
        for i, char in enumerate(query):
            for replacement in self._get_keyboard_neighbors(char):
                variant = query[:i] + replacement + query[i + 1 :]
                if variant not in seen:
                    corrections.append(variant)
                    seen.add(variant)
                    if len(corrections) >= max_variants:
                        return corrections

        # Try swapping adjacent characters (transposition)
        for i in range(len(query) - 1):
            variant = query[:i] + query[i + 1] + query[i] + query[i + 2 :]
            if variant not in seen and len(variant) >= 3:
                corrections.append(variant)
                seen.add(variant)
                if len(corrections) >= max_variants:
                    return corrections

        return corrections[:max_variants]

    def _remove_duplicate_chars(self, s: str) -> str:
        """Remove consecutive duplicate characters."""
        if not s:
            return s
        result = [s[0]]
        for char in s[1:]:
            if char != result[-1]:
                result.append(char)
        return "".join(result)

    def _get_keyboard_neighbors(self, char: str) -> list[str]:
        """Get neighboring keys on a QWERTY keyboard."""
        keyboard = {
            "a": ["q", "w", "s", "z"],
            "b": ["v", "g", "h", "n"],
            "c": ["x", "d", "f", "v"],
            "d": ["s", "e", "r", "f", "c", "x"],
            "e": ["w", "s", "d", "r"],
            "f": ["d", "r", "t", "g", "v", "c"],
            "g": ["f", "t", "y", "h", "b", "v"],
            "h": ["g", "y", "u", "j", "n", "b"],
            "i": ["u", "j", "k", "o"],
            "j": ["h", "u", "i", "k", "m", "n"],
            "k": ["j", "i", "o", "l", "m"],
            "l": ["k", "o", "p"],
            "m": ["n", "j", "k"],
            "n": ["b", "h", "j", "m"],
            "o": ["i", "k", "l", "p"],
            "p": ["o", "l"],
            "q": ["w", "a"],
            "r": ["e", "d", "f", "t"],
            "s": ["a", "w", "e", "d", "x", "z"],
            "t": ["r", "f", "g", "y"],
            "u": ["y", "h", "j", "i"],
            "v": ["c", "f", "g", "b"],
            "w": ["q", "a", "s", "e"],
            "x": ["z", "s", "d", "c"],
            "y": ["t", "g", "h", "u"],
            "z": ["a", "s", "x"],
        }
        return keyboard.get(char.lower(), [])


__all__ = [
    "Suggestion",
    "SuggestionEngine",
    "SuggestionResult",
]
