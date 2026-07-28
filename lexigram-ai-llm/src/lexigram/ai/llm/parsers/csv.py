"""CSV Output Parser."""

from __future__ import annotations

import csv
import io
from typing import Any

from lexigram.ai.llm.structured.exceptions import ParseError
from lexigram.ai.llm.structured.parser import extract_json_block
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class CSVOutputParser:
    """Parse LLM responses into lists of dictionaries (CSV format).

    Extracts JSON array from the response and converts to list of dicts,
    where each dict represents a CSV row with column names as keys.

    Example:
        >>> parser = CSVOutputParser()
        >>> result = parser.parse('[{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]')
        >>> assert len(result) == 2
        >>> assert result[0]["name"] == "John"
    """

    def parse(self, text: str) -> list[dict[str, Any]]:
        """Parse text into a list of dictionaries.

        Args:
            text: Raw LLM response text that may contain JSON array.

        Returns:
            List of dictionaries, each representing a CSV row.

        Raises:
            ParseError: When JSON cannot be extracted or is not an array.
        """
        try:
            parsed = extract_json_block(text)
        except ValueError as exc:
            raise ParseError(str(exc)) from exc

        if not isinstance(parsed, list):
            raise ParseError(
                f"Expected JSON array for CSV, got {type(parsed).__name__}"
            )

        for i, item in enumerate(parsed):
            if not isinstance(item, dict):
                raise ParseError(f"Row {i} is not a dict, got {type(item).__name__}")

        logger.debug("csv_parsed", row_count=len(parsed))
        return parsed

    def parse_csv_string(self, text: str) -> list[dict[str, Any]]:
        """Parse raw CSV text (not JSON) into list of dictionaries.

        Args:
            text: Raw CSV text with header row.

        Returns:
            List of dictionaries, each representing a CSV row.

        Raises:
            ParseError: When CSV cannot be parsed.
        """
        text = text.strip()
        try:
            reader = csv.DictReader(io.StringIO(text))
            return list(reader)
        except csv.Error as exc:
            raise ParseError(f"Failed to parse CSV: {exc}") from exc

    def get_format_instructions(self) -> str:
        """Return format instructions for the LLM.

        Returns:
            Format instruction string telling the model to output a valid
            JSON array of objects.
        """
        return (
            "Your response should be a valid JSON array of objects. "
            "Each object represents a row with column names as keys. "
            "Do not include any text before or after the JSON array. "
            "Do not use markdown code fences."
        )


__all__ = ["CSVOutputParser"]
