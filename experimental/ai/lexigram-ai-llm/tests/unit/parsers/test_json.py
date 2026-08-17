"""Tests for JSONOutputParser."""

from __future__ import annotations

import pytest

from lexigram.ai.llm.parsers.json import JSONOutputParser
from lexigram.ai.llm.structured.exceptions import ParseError


class TestJSONOutputParser:
    """Test cases for JSONOutputParser."""

    def test_parse_valid_json(self) -> None:
        """Test parsing valid JSON string."""
        parser = JSONOutputParser()
        result = parser.parse('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_with_markdown_fence(self) -> None:
        """Test parsing JSON wrapped in markdown code fence."""
        parser = JSONOutputParser()
        result = parser.parse('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_json_with_plain_fence(self) -> None:
        """Test parsing JSON wrapped in plain markdown fence."""
        parser = JSONOutputParser()
        result = parser.parse('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON raises ParseError."""
        parser = JSONOutputParser()
        with pytest.raises(ParseError):
            parser.parse('not valid json')

    def test_get_format_instructions(self) -> None:
        """Test format instructions are returned."""
        parser = JSONOutputParser()
        instructions = parser.get_format_instructions()
        assert "JSON" in instructions
        assert len(instructions) > 0
