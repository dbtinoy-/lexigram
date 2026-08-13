"""Unit tests for search filters."""

import pytest
from lexigram.search.query.filters import (
    FilterValidator,
    FilterRule,
    FilterType,
    FilterProcessor,
    ValidationError
)

class TestFilterValidator:
    """Test FilterValidator functionality."""

    def test_validate_text(self):
        """Test text validation."""
        rule = FilterRule(field="title", type=FilterType.TEXT, min_length=3)
        validator = FilterValidator([rule])

        # Valid
        assert validator._validate_field("title", "hello", rule) == "hello"

        # Invalid (too short)
        with pytest.raises(ValidationError):
            validator._validate_field("title", "hi", rule)

        # Invalid type
        with pytest.raises(ValidationError):
            validator._validate_field("title", 123, rule)

    def test_validate_number(self):
        """Test number validation."""
        rule = FilterRule(field="age", type=FilterType.NUMBER, min_value=18)
        validator = FilterValidator([rule])

        assert validator._validate_field("age", 25, rule) == 25

        with pytest.raises(ValidationError):
            validator._validate_field("age", 16, rule)

    def test_validate_range(self):
        """Test range validation."""
        rule = FilterRule(field="price", type=FilterType.RANGE)
        validator = FilterValidator([rule])

        valid = {"gte": 10, "lte": 20}
        assert validator._validate_field("price", valid, rule) == valid

        # Invalid key
        with pytest.raises(ValidationError):
            validator._validate_field("price", {"invalid": 10}, rule)

    def test_full_validation(self):
        """Test full dictionary validation."""
        rules = [
            FilterRule(field="status", type=FilterType.TEXT, allowed_values={"active", "inactive"}),
            FilterRule(field="count", type=FilterType.NUMBER)
        ]
        validator = FilterValidator(rules)

        filters = {"status": "active", "count": 5}
        validated = validator.validate_filters(filters)
        assert validated == filters

        with pytest.raises(ValidationError):
            validator.validate_filters({"status": "unknown"})

class TestFilterProcessor:
    """Test FilterProcessor functionality."""

    def test_transform(self):
        """Test filter transformation."""
        processor = FilterProcessor()
        
        filters = {"tag": "  HELLO  "}
        transforms = {"tag": lambda x: x.strip().lower()}
        
        result = processor.process_filters(filters, transforms)
        assert result["tag"] == "hello"
