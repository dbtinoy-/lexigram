"""Unit tests for skills types (from lexigram-contracts)."""

from __future__ import annotations

import pytest
from lexigram.contracts.ai.skills import (
    SkillDefinition,
    SkillParameter,
    SkillResult,
)


class TestSkillParameter:
    """Tests for SkillParameter dataclass."""

    def test_required_parameter(self) -> None:
        """Test creating a required parameter."""
        param = SkillParameter(
            name="query",
            type="string",
            description="Search query",
            required=True,
        )
        assert param.name == "query"
        assert param.type == "string"
        assert param.required is True

    def test_optional_parameter(self) -> None:
        """Test creating an optional parameter with default."""
        param = SkillParameter(
            name="limit",
            type="integer",
            description="Result limit",
            required=False,
            default=10,
        )
        assert param.required is False
        assert param.default == 10

    def test_parameter_with_enum(self) -> None:
        """Test parameter with enum values."""
        param = SkillParameter(
            name="format",
            type="string",
            description="Output format",
            required=False,
            default="json",
            enum=["json", "xml", "csv"],
        )
        assert param.enum == ["json", "xml", "csv"]

    def test_parameter_with_bounds(self) -> None:
        """Test parameter with min/max values."""
        param = SkillParameter(
            name="count",
            type="integer",
            description="Count value",
            required=False,
            default=5,
            min_value=1,
            max_value=100,
        )
        assert param.min_value == 1
        assert param.max_value == 100

    def test_parameter_frozen(self) -> None:
        """Test that SkillParameter is immutable."""
        param = SkillParameter(
            name="test",
            type="string",
            description="Test",
        )
        with pytest.raises(AttributeError):
            param.name = "changed"  # type: ignore[assignment]


class TestSkillDefinition:
    """Tests for SkillDefinition dataclass."""

    def test_minimal_definition(self) -> None:
        """Test creating a minimal skill definition."""
        definition = SkillDefinition(
            name="test_skill",
            description="A test skill",
        )
        assert definition.name == "test_skill"
        assert definition.description == "A test skill"
        assert definition.category == "general"
        assert definition.cacheable is False

    def test_full_definition(self) -> None:
        """Test creating a full skill definition with all fields."""
        definition = SkillDefinition(
            name="math_calculate",
            description="Perform mathematical calculations",
            parameters_schema={
                "type": "object",
                "properties": {
                    "expression": {"type": "string"},
                },
            },
            returns_schema={"type": "number"},
            category="computation",
            requires_confirmation=False,
            cacheable=True,
            max_retries=3,
            timeout_seconds=60.0,
            permissions=["compute"],
            metadata={"version": "1.0"},
        )
        assert definition.category == "computation"
        assert definition.cacheable is True
        assert definition.max_retries == 3
        assert definition.timeout_seconds == 60.0
        assert definition.permissions == ["compute"]

    def test_definition_frozen(self) -> None:
        """Test that SkillDefinition is immutable."""
        definition = SkillDefinition(
            name="test",
            description="Test",
        )
        with pytest.raises(AttributeError):
            definition.name = "changed"  # type: ignore[assignment]


class TestSkillResult:
    """Tests for SkillResult dataclass."""

    def test_successful_result(self) -> None:
        """Test creating a successful skill result."""
        result = SkillResult(
            skill_name="test_skill",
            success=True,
            output={"answer": 42},
        )
        assert result.skill_name == "test_skill"
        assert result.success is True
        assert result.output == {"answer": 42}
        assert result.error is None

    def test_failed_result(self) -> None:
        """Test creating a failed skill result."""
        result = SkillResult(
            skill_name="test_skill",
            success=False,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.output is None

    def test_result_with_timing(self) -> None:
        """Test result with duration and cached flag."""
        result = SkillResult(
            skill_name="test_skill",
            success=True,
            output="done",
            duration_ms=150.5,
            cached=True,
        )
        assert result.duration_ms == 150.5
        assert result.cached is True

    def test_result_frozen(self) -> None:
        """Test that SkillResult is immutable."""
        result = SkillResult(
            skill_name="test",
            success=True,
            output="ok",
        )
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[assignment]