"""Tests for Lexigram exception hierarchy."""

import pytest

from lexigram.contracts.exceptions.base import LexigramError
from lexigram.contracts.exceptions.provider import ModuleError
from lexigram.exceptions import (
    ConfigurationError,
    DomainModelError,
    InjectionError,
    LexigramException,
    SerializationError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Tests for exception inheritance hierarchy."""

    def test_lexigram_exception_extends_lexigram_error(self) -> None:
        """LexigramException must extend LexigramError from contracts."""
        assert issubclass(LexigramException, LexigramError)

    def test_lexigram_exception_is_base(self) -> None:
        """LexigramException is the base for all framework exceptions."""
        assert issubclass(ConfigurationError, LexigramException)
        assert issubclass(InjectionError, LexigramException)
        assert issubclass(ValidationError, LexigramException)
        assert issubclass(SerializationError, LexigramException)
        assert issubclass(DomainModelError, LexigramException)
        # ModuleError is from contracts and inherits LexigramError, not LexigramException
        assert issubclass(ModuleError, LexigramError)

    def test_all_exceptions_inherit_from_exception(self) -> None:
        """All Lexigram exceptions inherit from Exception."""
        assert issubclass(LexigramException, Exception)
        assert issubclass(ConfigurationError, Exception)
        assert issubclass(InjectionError, Exception)
        assert issubclass(ValidationError, Exception)
        assert issubclass(SerializationError, Exception)
        assert issubclass(DomainModelError, Exception)
        assert issubclass(ModuleError, Exception)  # via LexigramError → Exception

    def test_all_exceptions_inherit_from_lexigram_error(self) -> None:
        """All domain exceptions inherit from LexigramError."""
        assert issubclass(LexigramException, LexigramError)
        assert issubclass(ConfigurationError, LexigramError)
        assert issubclass(InjectionError, LexigramError)


class TestExceptionMessages:
    """Tests for exception messages and instantiation."""

    def test_lexigram_exception_with_message(self) -> None:
        """LexigramException can be instantiated with a message."""
        msg = "Something went wrong"
        exc = LexigramException(msg)
        # LexigramError.__str__ includes the code prefix, but the message is present
        assert msg in str(exc)

    def test_lexigram_exception_message_attribute(self) -> None:
        """LexigramException stores message on .message attribute."""
        msg = "Something went wrong"
        exc = LexigramException(msg)
        assert exc.message == msg

    def test_configuration_error_with_context(self) -> None:
        """ConfigurationError includes context in message."""
        exc = ConfigurationError("Invalid setting: debug")
        assert "Invalid setting" in str(exc)

    def test_injection_error_with_service_name(self) -> None:
        """InjectionError includes service information."""
        exc = InjectionError("Cannot resolve: UserService")
        assert "UserService" in str(exc)

    def test_validation_error_with_message(self) -> None:
        """ValidationError includes message in string representation."""
        exc = ValidationError("email: Invalid email format")
        assert "email" in str(exc)
        assert "Invalid" in str(exc)


class TestExceptionChaining:
    """Tests for exception chaining."""

    def test_exception_with_cause(self) -> None:
        """Exceptions can chain from other exceptions."""
        original = ValueError("original error")
        exc = LexigramException("wrapped")
        exc.__cause__ = original
        assert exc.__cause__ is original

    def test_injection_error_chains_resolution_error(self) -> None:
        """InjectionError can chain from underlying errors."""
        original = RuntimeError("container error")
        exc = InjectionError("resolution failed")
        exc.__cause__ = original
        assert exc.__cause__ is original


class TestExceptionCatching:
    """Tests for exception catching patterns."""

    def test_catch_all_lexigram_exceptions(self) -> None:
        """Can catch all Lexigram exceptions with base class."""
        framework_errors = [
            ConfigurationError("config"),
            InjectionError("inject"),
            ValidationError("validation failed"),
            SerializationError("json"),
            DomainModelError("domain"),
        ]
        for error in framework_errors:
            assert isinstance(error, LexigramException)

        # ModuleError is from contracts — catches as LexigramError, not LexigramException
        assert isinstance(ModuleError("module"), LexigramError)

    def test_catch_all_as_lexigram_error(self) -> None:
        """Can catch all Lexigram exceptions as LexigramError."""
        errors = [
            ConfigurationError("config"),
            InjectionError("inject"),
            ValidationError("validation failed"),
        ]
        for error in errors:
            assert isinstance(error, LexigramError)

    def test_catch_specific_exception(self) -> None:
        """Can catch specific exception types."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("specific error")

    def test_catch_by_parent_exception(self) -> None:
        """Specific exceptions can be caught by parent type."""
        with pytest.raises(LexigramException):
            raise ValidationError("validation failed")
