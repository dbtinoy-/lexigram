"""Tests for exception types in lexigram-contracts."""


import pytest
from lexigram.contracts.exceptions.base import LexigramError
from lexigram.contracts.exceptions.domain import (
    DomainError,
    NotFoundError,
    ConflictError,
    ValidationError,
    SerializationError,
)
from lexigram.contracts.exceptions import (
    AuthenticationError,
    AuthorizationError,
    PermissionDeniedError,
    RateLimitError,
)


class TestLexigramError:
    """Tests for base LexigramError."""

    def test_error_creation(self) -> None:
        """Test creating basic error."""
        error = LexigramError(message="Test error")
        assert error.message == "Test error"
        assert error.code == "LEX_ERR_CORE_001"

    def test_error_with_details(self) -> None:
        """Test error with details."""
        error = LexigramError(message="Test error", details={"key": "value"})
        assert error.details["key"] == "value"

    def test_error_with_cause(self) -> None:
        """Test error with cause."""
        cause = ValueError("original error")
        error = LexigramError(message="Wrapped error", cause=cause)
        assert error.cause is cause

    def test_error_with_hint(self) -> None:
        """Test error with hint."""
        error = LexigramError(message="Error", hint="Try again later")
        assert error.hint == "Try again later"

    def test_error_str_representation(self) -> None:
        """Test error string representation."""
        error = LexigramError(message="Test message")
        assert "[LEX_ERR_CORE_001]" in str(error)
        assert "Test message" in str(error)


class TestDomainError:
    """Tests for DomainError base class."""

    def test_domain_error_creation(self) -> None:
        """Test creating domain error."""
        error = DomainError("Domain rule violated")
        assert "Domain rule violated" in str(error)


class TestNotFoundError:
    """Tests for NotFoundError."""

    def test_not_found_error_creation(self) -> None:
        """Test creating not found error."""
        error = NotFoundError("Resource not found")
        assert "Resource not found" in str(error)


class TestConflictError:
    """Tests for ConflictError."""

    def test_conflict_error_creation(self) -> None:
        """Test creating conflict error."""
        error = ConflictError("Resource already exists")
        assert "Resource already exists" in str(error)


class TestValidationError:
    """Tests for ValidationError."""

    def test_validation_error_creation(self) -> None:
        """Test creating validation error."""
        error = ValidationError("Invalid input")
        assert "Invalid input" in str(error)


class TestSerializationError:
    """Tests for SerializationError."""

    def test_serialization_error_creation(self) -> None:
        """Test creating serialization error."""
        error = SerializationError("Failed to serialize")
        assert "Failed to serialize" in str(error)


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_auth_error_creation(self) -> None:
        """Test creating authentication error."""
        error = AuthenticationError("Invalid credentials")
        assert "Invalid credentials" in str(error)


class TestAuthorizationError:
    """Tests for AuthorizationError."""

    def test_authz_error_creation(self) -> None:
        """Test creating authorization error."""
        error = AuthorizationError("Access denied")
        assert "Access denied" in str(error)


class TestPermissionDeniedError:
    """Tests for PermissionDeniedError."""

    def test_permission_error_creation(self) -> None:
        """Test creating permission denied error."""
        error = PermissionDeniedError("No permission")
        assert "No permission" in str(error)


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_rate_limit_error_creation(self) -> None:
        """Test creating rate limit error."""
        error = RateLimitError("Too many requests")
        assert "Too many requests" in str(error)