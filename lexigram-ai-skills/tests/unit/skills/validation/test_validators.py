"""Tests for parameter validation."""

from __future__ import annotations

from lexigram.ai.skills.validation.schema import validate_params


class TestValidateParams:
    """Tests for validate_params function."""

    def test_required_field_missing(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }
        params = {"age": 25}

        errors = validate_params(params, schema)

        assert len(errors) == 1
        assert "'name' is required" in errors[0]

    def test_type_mismatch(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
            },
            "required": [],
        }
        params = {"count": "not an integer"}

        errors = validate_params(params, schema)

        assert len(errors) == 1
        assert "must be of type 'integer'" in errors[0]

    def test_enum_value_outside_allowed(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive"]},
            },
            "required": [],
        }
        params = {"status": "pending"}

        errors = validate_params(params, schema)

        assert len(errors) == 1
        assert "must be one of" in errors[0]

    def test_minimum_maximum_bounds(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100},
            },
            "required": [],
        }

        errors = validate_params({"score": -5}, schema)
        assert len(errors) == 1
        assert "must be >= 0" in errors[0]

        errors = validate_params({"score": 150}, schema)
        assert len(errors) == 1
        assert "must be <= 100" in errors[0]

        errors = validate_params({"score": 50}, schema)
        assert errors == []

    def test_min_length_max_length_bounds(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "username": {"type": "string", "minLength": 3, "maxLength": 20},
            },
            "required": [],
        }

        errors = validate_params({"username": "ab"}, schema)
        assert len(errors) == 1
        assert "length >= 3" in errors[0]

        errors = validate_params({"username": "a" * 25}, schema)
        assert len(errors) == 1
        assert "length <= 20" in errors[0]

        errors = validate_params({"username": "validuser"}, schema)
        assert errors == []

    def test_valid_params_returns_empty_list(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "active": {"type": "boolean"},
            },
            "required": ["name"],
        }
        params = {"name": "Alice", "age": 30, "active": True}

        errors = validate_params(params, schema)

        assert errors == []

    def test_empty_schema_returns_empty(self) -> None:
        params = {"any": "value"}
        errors = validate_params(params, {})
        assert errors == []

    def test_multiple_errors_accumulated(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 3},
                "count": {"type": "integer", "minimum": 1},
            },
            "required": ["name", "count"],
        }
        params = {"name": "ab", "count": 0}

        errors = validate_params(params, schema)

        assert len(errors) == 2
