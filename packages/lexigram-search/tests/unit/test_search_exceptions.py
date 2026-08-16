"""Tests for search exception classes."""

from __future__ import annotations

import pytest

from lexigram.search.exceptions import (
    BackendError,
    IndexNotFoundError,
    SearchError,
    SearchValidationError,
)


class TestSearchErrorCode:
    """Test SearchError error codes."""

    def test_search_error_code(self) -> None:
        """Test SearchError has correct error code."""
        error = SearchError("test message")
        assert error._code == "LEX_ERR_SEARCH_001"

    def test_search_error_message(self) -> None:
        """Test SearchError message is preserved."""
        error = SearchError("Test search failed")
        assert error.message == "Test search failed"

    def test_search_error_str(self) -> None:
        """Test SearchError string representation."""
        error = SearchError("test")
        assert "test" in str(error)

    def test_search_error_inheritance(self) -> None:
        """Test SearchError inherits from LexigramError."""
        from lexigram.contracts.exceptions import LexigramError

        error = SearchError("test")
        assert isinstance(error, LexigramError)


class TestIndexNotFoundErrorCode:
    """Test IndexNotFoundError error codes."""

    def test_index_not_found_code(self) -> None:
        """Test IndexNotFoundError has correct error code."""
        error = IndexNotFoundError("my-index")
        assert error._code == "LEX_ERR_SEARCH_002"

    def test_index_not_found_message_includes_index(self) -> None:
        """Test IndexNotFoundError message includes index name."""
        error = IndexNotFoundError("test-index")
        assert "test-index" in str(error)

    def test_index_not_found_inheritance(self) -> None:
        """Test IndexNotFoundError inherits from DomainError."""
        from lexigram.contracts.exceptions import DomainError

        error = IndexNotFoundError("index")
        assert isinstance(error, DomainError)


class TestBackendErrorCode:
    """Test BackendError error codes."""

    def test_backend_error_code(self) -> None:
        """Test BackendError has correct error code."""
        error = BackendError("Connection failed")
        assert error._code == "LEX_ERR_SEARCH_003"

    def test_backend_error_message(self) -> None:
        """Test BackendError message is preserved."""
        error = BackendError("Elasticsearch unavailable")
        assert error.message == "Elasticsearch unavailable"

    def test_backend_error_inheritance(self) -> None:
        """Test BackendError inherits from InfrastructureError."""
        from lexigram.contracts.exceptions import InfrastructureError

        error = BackendError("test")
        assert isinstance(error, InfrastructureError)


class TestSearchValidationErrorCode:
    """Test SearchValidationError error codes."""

    def test_search_validation_error_code(self) -> None:
        """Test SearchValidationError has correct error code."""
        error = SearchValidationError("Invalid query syntax")
        assert error._code == "LEX_ERR_SEARCH_004"

    def test_search_validation_error_message(self) -> None:
        """Test SearchValidationError message is preserved."""
        error = SearchValidationError("Query too complex")
        assert error.message == "Query too complex"

    def test_search_validation_inheritance(self) -> None:
        """Test SearchValidationError inherits from SearchError."""
        error = SearchValidationError("validation failed")
        assert isinstance(error, SearchError)


class TestExceptionChaining:
    """Test exception chaining."""

    def test_search_error_with_cause(self) -> None:
        """Test SearchError can be chained from another exception."""
        original = ValueError("original cause")
        error = SearchError("wrapped")
        error.__cause__ = original
        assert error.__cause__ is original

    def test_backend_error_with_cause(self) -> None:
        """Test BackendError can be chained from another exception."""
        original = ConnectionError("connection lost")
        error = BackendError("backend failed")
        error.__cause__ = original
        assert error.__cause__ is original


class TestExceptionEquality:
    """Test exception equality."""

    def test_search_error_equality(self) -> None:
        """Test SearchError equality based on message."""
        error1 = SearchError("same message")
        error2 = SearchError("same message")
        # Exceptions with same message should have same repr
        assert repr(error1) == repr(error2)


class TestExceptionsExports:
    """Test that all exceptions are properly exported."""

    def test_all_exported(self) -> None:
        """Test all exceptions are in __all__."""
        from lexigram.search.exceptions import __all__

        assert "SearchError" in __all__
        assert "IndexNotFoundError" in __all__
        assert "BackendError" in __all__
        assert "SearchValidationError" in __all__

    def test_can_import_from_module(self) -> None:
        """Test exceptions can be imported directly."""
        from lexigram.search.exceptions import (
            SearchError,
            IndexNotFoundError,
            BackendError,
            SearchValidationError,
        )

        assert SearchError is not None
        assert IndexNotFoundError is not None
        assert BackendError is not None
        assert SearchValidationError is not None


class TestExceptionRaising:
    """Test exceptions can be raised and caught."""

    def test_raise_and_catch_search_error(self) -> None:
        """Test SearchError can be raised and caught."""
        with pytest.raises(SearchError):
            raise SearchError("test error")

    def test_raise_and_catch_index_not_found(self) -> None:
        """Test IndexNotFoundError can be raised and caught."""
        with pytest.raises(IndexNotFoundError):
            raise IndexNotFoundError("missing-index")

    def test_raise_and_catch_backend_error(self) -> None:
        """Test BackendError can be raised and caught."""
        with pytest.raises(BackendError):
            raise BackendError("backend failure")

    def test_raise_and_catch_validation_error(self) -> None:
        """Test SearchValidationError can be raised and caught."""
        with pytest.raises(SearchValidationError):
            raise SearchValidationError("invalid")

    def test_catch_as_base(self) -> None:
        """Test specific exceptions can be caught as LexigramError."""
        from lexigram.contracts.exceptions import LexigramError

        with pytest.raises(LexigramError):
            raise IndexNotFoundError("index")

    def test_catch_infrastructure(self) -> None:
        """Test BackendError can be caught as infrastructure error."""
        from lexigram.contracts.exceptions import InfrastructureError

        with pytest.raises(InfrastructureError):
            raise BackendError("ES down")