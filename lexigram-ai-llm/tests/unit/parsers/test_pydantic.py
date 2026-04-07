"""Tests for PydanticOutputParser."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from lexigram.ai.llm.parsers.pydantic import PydanticOutputParser
from lexigram.ai.llm.structured.exceptions import ParseError, SchemaValidationError


class User(BaseModel):
    name: str
    age: int


class TestPydanticOutputParser:
    """Test cases for PydanticOutputParser."""

    def test_parse_valid_pydantic(self) -> None:
        """Test parsing valid JSON into Pydantic model."""
        parser = PydanticOutputParser(User)
        result = parser.parse('{"name": "John", "age": 30}')
        assert result.name == "John"
        assert result.age == 30

    def test_parse_with_markdown_fence(self) -> None:
        """Test parsing JSON wrapped in markdown fence."""
        parser = PydanticOutputParser(User)
        result = parser.parse('```json\n{"name": "Jane", "age": 25}\n```')
        assert result.name == "Jane"
        assert result.age == 25

    def test_parse_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON raises ParseError."""
        parser = PydanticOutputParser(User)
        with pytest.raises(ParseError):
            parser.parse("not valid json")

    def test_parse_invalid_schema_raises_error(self) -> None:
        """Test that validation failure raises SchemaValidationError."""
        parser = PydanticOutputParser(User)
        with pytest.raises(SchemaValidationError):
            parser.parse('{"name": "John"}')  # missing required field 'age'

    def test_get_format_instructions(self) -> None:
        """Test format instructions are returned."""
        parser = PydanticOutputParser(User)
        instructions = parser.get_format_instructions()
        assert "JSON" in instructions
        assert "schema" in instructions.lower()
