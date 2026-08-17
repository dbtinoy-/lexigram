"""Tests for admin specifications."""

import pytest

from lexigram.admin.lib.specifications import AndSpecification, ComparisonOperator, FieldSpecification


class TestComparisonOperator:
    """Tests for ComparisonOperator enum."""

    def test_comparison_operator_values(self) -> None:
        """Test ComparisonOperator enum values."""
        assert ComparisonOperator.EQ.value == "eq"
        assert ComparisonOperator.NE.value == "ne"
        assert ComparisonOperator.GT.value == "gt"
        assert ComparisonOperator.GTE.value == "gte"
        assert ComparisonOperator.LT.value == "lt"
        assert ComparisonOperator.LTE.value == "lte"
        assert ComparisonOperator.IN.value == "in"
        assert ComparisonOperator.CONTAINS.value == "contains"
        assert ComparisonOperator.STARTSWITH.value == "startswith"
        assert ComparisonOperator.ENDSWITH.value == "endswith"

    def test_comparison_operator_members(self) -> None:
        """Test ComparisonOperator has expected members."""
        members = list(ComparisonOperator)
        assert len(members) == 10


class TestFieldSpecification:
    """Tests for FieldSpecification class."""

    def test_field_specification_creation(self) -> None:
        """Test FieldSpecification creation."""
        spec = FieldSpecification(field="name", value="John", operator=ComparisonOperator.EQ)
        assert spec.field == "name"
        assert spec.value == "John"
        assert spec.operator == ComparisonOperator.EQ

    def test_field_specification_default_operator(self) -> None:
        """Test FieldSpecification default operator."""
        spec = FieldSpecification(field="name", value="John")
        assert spec.operator == ComparisonOperator.EQ

    def test_field_specification_and_operator(self) -> None:
        """Test FieldSpecification & operator."""
        spec1 = FieldSpecification(field="name", value="John")
        spec2 = FieldSpecification(field="age", value=30)
        combined = spec1 & spec2
        assert isinstance(combined, AndSpecification)


class TestAndSpecification:
    """Tests for AndSpecification class."""

    def test_and_specification_creation(self) -> None:
        """Test AndSpecification creation."""
        spec1 = FieldSpecification(field="name", value="John")
        spec2 = FieldSpecification(field="age", value=30)
        and_spec = AndSpecification(spec1, spec2)
        assert and_spec is not None
