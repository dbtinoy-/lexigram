from dataclasses import dataclass
"""Tests for structured output functionality.

Test coverage:
- JSONExtractor: extract, extract_array, edge cases
- StructuredOutputParser: parse, parse_array, schema generation
- ResponseFormatter: type conversions
- Helper functions: create_json_mode_messages, complete_with_schema, complete_with_json
"""

from datetime import datetime

from lexigram.validation import Field
from lexigram.domain import DomainModel
from lexigram.domain import DomainModel
import pytest

from lexigram.ai.llm import (
    JSONExtractor,
    ParseError,
    ResponseFormatter,
    SchemaValidationError,
    StructuredOutputError,
    StructuredOutputParser,
    complete_with_json,
    complete_with_schema,
    create_json_mode_messages,
)
from support.mock_clients import MockLLMClient
from lexigram.ai.llm.types import Completion

# =============================================================================
# Test Models
# =============================================================================


@dataclass(init=False)
class Person(DomainModel):
    """Test person model."""

    name: str = Field(..., description="Full name")
    age: int = Field(..., gt=0, description="Age in years")
    email: str | None = Field(None, description="Email address")


@dataclass(init=False)
class Product(DomainModel):
    """Test product model."""

    name: str
    price: float
    in_stock: bool = True


# =============================================================================
# Test JSONExtractor
# =============================================================================


class TestJSONExtractor:
    """Test JSON extraction from various formats."""

    def test_extract_pure_json(self):
        """Test extracting pure JSON."""
        extractor = JSONExtractor()
        text = '{"key": "value", "number": 42}'
        result = extractor.extract(text)
        assert result == {"key": "value", "number": 42}

    def test_extract_from_code_block(self):
        """Test extracting JSON from markdown code block."""
        extractor = JSONExtractor()
        text = """Here's the data:
        ```json
        {"name": "Alice", "age": 30}
        ```
        """
        result = extractor.extract(text)
        assert result == {"name": "Alice", "age": 30}

    def test_extract_from_code_block_no_language(self):
        """Test extracting from code block without language marker."""
        extractor = JSONExtractor()
        text = """```
        {"status": "ok"}
        ```"""
        result = extractor.extract(text)
        assert result == {"status": "ok"}

    def test_extract_from_text(self):
        """Test extracting JSON embedded in text."""
        extractor = JSONExtractor()
        text = 'The answer is {"value": 42} and that is correct.'
        result = extractor.extract(text)
        assert result == {"value": 42}

    def test_extract_multiple(self):
        """Test extracting multiple JSON objects."""
        extractor = JSONExtractor()
        text = """
        First: {"id": 1}
        Second: {"id": 2}
        """
        results = extractor.extract(text, multiple=True)
        assert results == [{"id": 1}, {"id": 2}]

    def test_extract_array(self):
        """Test extracting JSON array."""
        extractor = JSONExtractor()
        text = '[{"id": 1}, {"id": 2}, {"id": 3}]'
        result = extractor.extract_array(text)
        assert result == [{"id": 1}, {"id": 2}, {"id": 3}]

    def test_extract_array_from_code_block(self):
        """Test extracting array from code block."""
        extractor = JSONExtractor()
        text = """```json
        [1, 2, 3]
        ```"""
        result = extractor.extract_array(text)
        assert result == [1, 2, 3]

    def test_extract_invalid_json_raises_error(self):
        """Test that invalid JSON raises ParseError."""
        extractor = JSONExtractor()
        with pytest.raises(ParseError):
            extractor.extract("This is not JSON")

    def test_extract_array_non_array_raises_error(self):
        """Test that non-array raises error in extract_array."""
        extractor = JSONExtractor()
        with pytest.raises(ParseError):
            extractor.extract_array('{"not": "an array"}')

    def test_extract_nested_json(self):
        """Test extracting nested JSON objects."""
        extractor = JSONExtractor()
        text = '{"user": {"name": "Alice", "age": 30}, "active": true}'
        result = extractor.extract(text)
        assert result == {"user": {"name": "Alice", "age": 30}, "active": True}


# =============================================================================
# Test StructuredOutputParser
# =============================================================================


class TestStructuredOutputParser:
    """Test schema-based parsing and validation."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON against schema."""
        parser = StructuredOutputParser(Person)
        completion = Completion(
            content='{"name": "Alice", "age": 30}',
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        person = parser.parse(completion)
        assert person.name == "Alice"
        assert person.age == 30

    def test_parse_with_optional_fields(self):
        """Test parsing with optional fields."""
        parser = StructuredOutputParser(Person)
        completion = Completion(
            content='{"name": "Bob", "age": 25, "email": "bob@example.com"}',
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        person = parser.parse(completion)
        assert person.name == "Bob"
        assert person.age == 25
        assert person.email == "bob@example.com"

    def test_parse_from_code_block(self):
        """Test parsing JSON from code block."""
        parser = StructuredOutputParser(Person)
        completion = Completion(
            content="""```json
            {"name": "Charlie", "age": 35}
            ```""",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        person = parser.parse(completion)
        assert person.name == "Charlie"
        assert person.age == 35

    def test_parse_missing_required_field_raises_error(self):
        """Test that missing required field raises SchemaValidationError."""
        parser = StructuredOutputParser(Person)
        completion = Completion(
            content='{"name": "Alice"}',  # Missing 'age'
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        with pytest.raises(SchemaValidationError):
            parser.parse(completion)

    def test_parse_invalid_field_value_raises_error(self):
        """Test that invalid field value raises SchemaValidationError."""
        parser = StructuredOutputParser(Person)
        completion = Completion(
            content='{"name": "Alice", "age": -5}',  # Age must be > 0
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        with pytest.raises(SchemaValidationError):
            parser.parse(completion)

    def test_parse_array(self):
        """Test parsing array of objects."""
        parser = StructuredOutputParser(Person)
        completion = Completion(
            content="""[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25}
            ]""",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        people = parser.parse_array(completion)
        assert len(people) == 2
        assert people[0].name == "Alice"
        assert people[1].name == "Bob"

    def test_parse_array_from_code_block(self):
        """Test parsing array from code block."""
        parser = StructuredOutputParser(Person)
        completion = Completion(
            content="""```json
            [
                {"name": "Charlie", "age": 35}
            ]
            ```""",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        people = parser.parse_array(completion)
        assert len(people) == 1
        assert people[0].name == "Charlie"

    def test_parse_array_non_array_raises_error(self):
        """Test that non-array raises error in parse_array."""
        parser = StructuredOutputParser(Person)
        completion = Completion(
            content='{"name": "Alice", "age": 30}',
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        with pytest.raises(ParseError):
            parser.parse_array(completion)

    def test_get_json_schema(self):
        """Test getting JSON schema."""
        parser = StructuredOutputParser(Person)
        schema = parser.get_json_schema()
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]

    def test_get_schema_prompt(self):
        """Test generating schema prompt."""
        parser = StructuredOutputParser(Person)
        prompt = parser.get_schema_prompt()
        assert "name" in prompt
        assert "age" in prompt
        assert "required" in prompt or "optional" in prompt

    def test_parse_non_strict_mode(self):
        """Test non-strict mode handling."""
        parser = StructuredOutputParser(Person, strict=False)
        completion = Completion(
            content="Not valid JSON",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        # Should still raise ParseError even in non-strict
        with pytest.raises(ParseError):
            parser.parse(completion)


# =============================================================================
# Test ResponseFormatter
# =============================================================================


class TestResponseFormatter:
    """Test response type conversion."""

    def test_to_json(self):
        """Test converting to JSON."""
        formatter = ResponseFormatter()
        completion = Completion(
            content='{"key": "value"}',
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        result = formatter.to_json(completion)
        assert result == {"key": "value"}

    def test_to_string(self):
        """Test converting to string."""
        formatter = ResponseFormatter()
        completion = Completion(
            content="  Hello World  ",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        result = formatter.to_string(completion)
        assert result == "Hello World"

    def test_to_string_no_strip(self):
        """Test converting to string without stripping."""
        formatter = ResponseFormatter()
        completion = Completion(
            content="  Hello  ",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        result = formatter.to_string(completion, strip=False)
        assert result == "  Hello  "

    def test_to_int_pure_number(self):
        """Test converting pure number to int."""
        formatter = ResponseFormatter()
        completion = Completion(
            content="42",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        result = formatter.to_int(completion)
        assert result == 42
        assert isinstance(result, int)

    def test_to_int_from_text(self):
        """Test extracting int from text."""
        formatter = ResponseFormatter()
        completion = Completion(
            content="The answer is 42",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        result = formatter.to_int(completion)
        assert result == 42

    def test_to_int_negative(self):
        """Test converting negative number."""
        formatter = ResponseFormatter()
        completion = Completion(
            content="-10",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        result = formatter.to_int(completion)
        assert result == -10

    def test_to_int_invalid_raises_error(self):
        """Test that invalid int raises ParseError."""
        formatter = ResponseFormatter()
        completion = Completion(
            content="not a number",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        with pytest.raises(ParseError):
            formatter.to_int(completion)

    def test_to_float_pure_number(self):
        """Test converting pure number to float."""
        formatter = ResponseFormatter()
        completion = Completion(
            content="3.14",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        result = formatter.to_float(completion)
        assert result == 3.14
        assert isinstance(result, float)

    def test_to_float_from_text(self):
        """Test extracting float from text."""
        formatter = ResponseFormatter()
        completion = Completion(
            content="The value is 3.14159",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        result = formatter.to_float(completion)
        assert abs(result - 3.14159) < 0.0001

    def test_to_bool_true_variants(self):
        """Test converting various true values."""
        formatter = ResponseFormatter()

        for value in ["true", "True", "yes", "Yes", "1", "y", "Y"]:
            completion = Completion(
                content=value,
                model="mock",
                role="assistant",
                usage=None,
                timestamp=datetime.now(),
            )
            result = formatter.to_bool(completion)
            assert result is True

    def test_to_bool_false_variants(self):
        """Test converting various false values."""
        formatter = ResponseFormatter()

        for value in ["false", "False", "no", "No", "0", "n", "N"]:
            completion = Completion(
                content=value,
                model="mock",
                role="assistant",
                usage=None,
                timestamp=datetime.now(),
            )
            result = formatter.to_bool(completion)
            assert result is False

    def test_to_bool_invalid_raises_error(self):
        """Test that invalid bool raises ParseError."""
        formatter = ResponseFormatter()
        completion = Completion(
            content="maybe",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        with pytest.raises(ParseError):
            formatter.to_bool(completion)

    def test_to_list_newline_separated(self):
        """Test converting newline-separated list."""
        formatter = ResponseFormatter()
        completion = Completion(
            content="Apple\nBanana\nCherry",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        result = formatter.to_list(completion)
        assert result == ["Apple", "Banana", "Cherry"]

    def test_to_list_json_array(self):
        """Test converting JSON array to list."""
        formatter = ResponseFormatter()
        completion = Completion(
            content='["Apple", "Banana", "Cherry"]',
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        result = formatter.to_list(completion)
        assert result == ["Apple", "Banana", "Cherry"]

    def test_to_list_custom_separator(self):
        """Test converting with custom separator."""
        formatter = ResponseFormatter()
        completion = Completion(
            content="Apple, Banana, Cherry",
            model="mock",
            role="assistant",
            usage=None,
            timestamp=datetime.now(),
        )
        result = formatter.to_list(completion, separator=", ")
        assert result == ["Apple", "Banana", "Cherry"]


# =============================================================================
# Test Helper Functions
# =============================================================================


class TestHelperFunctions:
    """Test helper functions for JSON mode."""

    def test_create_json_mode_messages_basic(self):
        """Test creating basic JSON mode messages."""
        messages = create_json_mode_messages("Test prompt")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "JSON" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Test prompt"

    def test_create_json_mode_messages_with_schema(self):
        """Test creating messages with schema."""
        messages = create_json_mode_messages("Extract person", schema=Person)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        # Schema should be in user message
        assert "name" in messages[1]["content"]
        assert "age" in messages[1]["content"]

    def test_create_json_mode_messages_custom_system(self):
        """Test creating messages with custom system prompt."""
        custom = "Custom system prompt"
        messages = create_json_mode_messages("Test", system_prompt=custom)
        assert messages[0]["content"] == custom

    @pytest.mark.asyncio
    async def test_complete_with_schema(self):
        """Test complete_with_schema helper."""
        client = MockLLMClient()

        # Override mock to return valid JSON
        original_complete = client.complete

        async def mock_complete(messages, **kwargs):
            from lexigram.result import Ok
            completion = (await original_complete(messages, **kwargs)).unwrap()
            completion.content = '{"name": "Alice", "age": 30}'
            return Ok(completion)

        client.complete = mock_complete

        person = await complete_with_schema(client, "Extract person", schema=Person)
        assert person.name == "Alice"
        assert person.age == 30

    @pytest.mark.asyncio
    async def test_complete_with_json(self):
        """Test complete_with_json helper."""
        client = MockLLMClient()

        # Override mock to return JSON
        original_complete = client.complete

        async def mock_complete(messages, **kwargs):
            from lexigram.result import Ok
            completion = (await original_complete(messages, **kwargs)).unwrap()
            completion.content = '{"status": "ok", "count": 5}'
            return Ok(completion)

        client.complete = mock_complete

        data = await complete_with_json(client, "Generate data")
        assert data == {"status": "ok", "count": 5}


# =============================================================================
# Test Error Hierarchy
# =============================================================================


class TestErrorHierarchy:
    """Test error hierarchy."""

    def test_structured_output_error_base(self):
        """Test base exception."""
        error = StructuredOutputError("Test error")
        assert "Test error" in str(error)
        assert isinstance(error, Exception)

    def test_parse_error_inheritance(self):
        """Test ParseError inherits from StructuredOutputError."""
        error = ParseError("Parse failed")
        assert isinstance(error, StructuredOutputError)
        assert isinstance(error, Exception)

    def test_validation_error_inheritance(self):
        """Test SchemaValidationError inherits from StructuredOutputError."""
        error = SchemaValidationError("Validation failed")
        assert isinstance(error, StructuredOutputError)
        assert isinstance(error, Exception)
