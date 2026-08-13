"""JSON Output Parser."""

from __future__ import annotations

from typing import Any

from lexigram.ai.llm.structured.exceptions import ParseError
from lexigram.ai.llm.structured.parser import extract_json_block
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class JSONOutputParser:
    """Parse LLM responses into JSON dicts.

    Handles common LLM output patterns like markdown code fences,
    prose before/after JSON, and malformed JSON.

    Example:
        >>> parser = JSONOutputParser()
        >>> result = parser.parse('{"key": "value"}')
        >>> assert result == {"key": "value"}
    """

    def parse(self, text: str) -> dict[str, Any]:
        """Parse text into a JSON dict.

        Args:
            text: Raw LLM response text that may contain JSON.

        Returns:
            Parsed JSON as a dict.

        Raises:
            ParseError: When JSON cannot be extracted or parsed.
        """
        try:
            parsed = extract_json_block(text)
        except ValueError as exc:
            raise ParseError(str(exc)) from exc

        if not isinstance(parsed, dict):
            raise ParseError(f"Expected JSON object, got {type(parsed).__name__}")

        logger.debug("json_parsed", keys=list(parsed.keys()))
        return parsed

    def get_format_instructions(self) -> str:
        """Return format instructions for the LLM.

        Returns:
            Format instruction string telling the model to output valid JSON.
        """
        return (
            "Your response should be a valid JSON object. "
            "Do not include any text before or after the JSON. "
            "Do not use markdown code fences."
        )


__all__ = ["JSONOutputParser"]
