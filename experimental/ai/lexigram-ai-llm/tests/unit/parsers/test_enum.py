"""Tests for EnumOutputParser."""

from __future__ import annotations

from enum import Enum

import pytest

from lexigram.ai.llm.parsers.enum import EnumOutputParser
from lexigram.ai.llm.structured.exceptions import ParseError


class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class TestEnumOutputParser:
    """Test cases for EnumOutputParser."""

    def test_parse_valid_enum_string(self) -> None:
        """Test parsing valid enum string."""
        parser = EnumOutputParser(Status)
        result = parser.parse('"active"')
        assert result == Status.ACTIVE

    def test_parse_invalid_enum_raises_error(self) -> None:
        """Test that invalid enum value raises ParseError."""
        parser = EnumOutputParser(Status)
        with pytest.raises(ParseError) as exc_info:
            parser.parse('"invalid"')
        assert "Invalid enum value" in str(exc_info.value)

    def test_parse_non_string_raises_error(self) -> None:
        """Test that non-string/non-int raises ParseError."""
        parser = EnumOutputParser(Status)
        with pytest.raises(ParseError):
            parser.parse('[1, 2, 3]')

    def test_get_format_instructions(self) -> None:
        """Test format instructions are returned."""
        parser = EnumOutputParser(Status)
        instructions = parser.get_format_instructions()
        assert "active" in instructions
        assert "inactive" in instructions
