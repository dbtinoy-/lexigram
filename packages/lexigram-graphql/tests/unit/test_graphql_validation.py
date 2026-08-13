"""Unit tests for GraphQL validation."""

import pytest
import strawberry
from graphql import parse

from lexigram.graphql.core.validation import (
    SchemaValidator,
    ValidationResult,
    validate_query,
)
from lexigram.graphql.exceptions import QueryTooDeepError
from lexigram.graphql.security.depth import DepthLimitValidator

@strawberry.type
class User:
    id: strawberry.ID
    name: str
    friends: list["User"]

@strawberry.type
class Query:
    @strawberry.field
    def me(self) -> User:
        return User(id=strawberry.ID("1"), name="Me", friends=[])

schema = strawberry.Schema(query=Query)


class TestDepthLimitValidator:
    """Test DepthLimitValidator — the canonical depth analysis implementation."""

    def test_get_depth_simple(self):
        """Test depth calculation for a simple query."""
        document = parse("{ me { name } }")
        validator = DepthLimitValidator()
        assert validator.get_depth(document) == 1

    def test_get_depth_nested(self):
        """Test depth calculation for a nested query."""
        document = parse("{ me { friends { name } } }")
        validator = DepthLimitValidator()
        assert validator.get_depth(document) == 2

    def test_validate_depth_exceeded_raises(self):
        """Test that validate() raises QueryTooDeepError when depth is exceeded."""
        document = parse("{ me { friends { friends { name } } } }")
        validator = DepthLimitValidator(max_depth=2)

        with pytest.raises(QueryTooDeepError):
            validator.validate(document)

    def test_validate_depth_within_limit(self):
        """Test that validate() passes when depth is within limit."""
        document = parse("{ me { name } }")
        validator = DepthLimitValidator(max_depth=5)
        # Should not raise
        validator.validate(document)

    def test_introspection_skipped(self):
        """Test that introspection fields are ignored in depth calculation."""
        document = parse("{ __schema { types { name } } }")
        validator = DepthLimitValidator(max_depth=1, ignore_introspection=True)
        # Should not raise since __schema is introspection
        validator.validate(document)

class TestSchemaValidator:
    """Test SchemaValidator functionality."""

    @pytest.fixture
    def validator(self):
        return SchemaValidator(schema, max_depth=5, max_aliases=3)

    def test_validate_valid_query(self, validator):
        """Test validating a valid query."""
        query = "{ me { name } }"
        result = validator.validate_query(query)
        
        assert result.is_valid
        assert not result.errors

    def test_validate_invalid_query_syntax(self, validator):
        """Test validating query with syntax error."""
        query = "{ me { name " # Missing brace
        result = validator.validate_query(query)
        
        assert not result.is_valid
        assert "scan error" in result.errors[0] or "Syntax Error" in result.errors[0] or "parse error" in result.errors[0]

    def test_validate_invalid_query_schema(self, validator):
        """Test validating query against schema rules."""
        query = "{ me { unknownField } }"
        result = validator.validate_query(query)
        
        assert not result.is_valid
        assert "Cannot query field" in result.errors[0]

    def test_validate_aliases_limit(self, validator):
        """Test validating alias limits."""
        # 4 aliases, max is 3
        query = """
        {
            a: me { name }
            b: me { name }
            c: me { name }
            d: me { name }
        }
        """
        result = validator.validate_query(query)
        
        assert not result.is_valid
        assert "aliases" in result.errors[0]

class TestValidateQueryHelper:
    """Test validate_query helper."""

    def test_validate_query_helper(self):
        """Test helper function."""
        query = "{ me { name } }"
        result = validate_query(schema, query)
        assert result.is_valid
