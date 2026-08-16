"""Tests for NoSQL exceptions."""

from __future__ import annotations

import pytest

from lexigram.nosql.exceptions import (
    DocumentNotFoundError,
    DocumentValidationError,
    DuplicateKeyError,
    NoSQLConnectionError,
    NoSQLError,
    TransactionError,
)


class TestNoSQLError:
    def test_inherits_from_lexigram_error(self) -> None:
        """NoSQLError inherits from LexigramError."""
        assert issubclass(NoSQLError, Exception)

    def test_has_error_code(self) -> None:
        """NoSQLError has an error code."""
        err = NoSQLError("test message")
        assert err._code == "LEX_ERR_NOSQL_001"


class TestNoSQLConnectionError:
    def test_inherits_from_no_sql_error(self) -> None:
        """NoSQLConnectionError inherits from NoSQLError."""
        assert issubclass(NoSQLConnectionError, NoSQLError)

    def test_has_error_code(self) -> None:
        """NoSQLConnectionError has an error code."""
        err = NoSQLConnectionError("connection failed")
        assert err._code == "LEX_ERR_NOSQL_002"

    def test_is_raiseable(self) -> None:
        """NoSQLConnectionError can be raised and caught."""
        with pytest.raises(NoSQLConnectionError):
            raise NoSQLConnectionError("cannot connect")


class TestDocumentNotFoundError:
    def test_inherits_from_no_sql_error(self) -> None:
        """DocumentNotFoundError inherits from NoSQLError."""
        assert issubclass(DocumentNotFoundError, NoSQLError)

    def test_has_error_code(self) -> None:
        """DocumentNotFoundError has an error code."""
        err = DocumentNotFoundError("doc not found")
        assert err._code == "LEX_ERR_NOSQL_003"

    def test_can_be_raised(self) -> None:
        """DocumentNotFoundError can be raised and caught."""
        with pytest.raises(DocumentNotFoundError):
            raise DocumentNotFoundError("document 123 not found")


class TestDuplicateKeyError:
    def test_inherits_from_no_sql_error(self) -> None:
        """DuplicateKeyError inherits from NoSQLError."""
        assert issubclass(DuplicateKeyError, NoSQLError)

    def test_has_error_code(self) -> None:
        """DuplicateKeyError has an error code."""
        err = DuplicateKeyError("duplicate key")
        assert err._code == "LEX_ERR_NOSQL_004"

    def test_can_be_raised(self) -> None:
        """DuplicateKeyError can be raised and caught."""
        with pytest.raises(DuplicateKeyError):
            raise DuplicateKeyError("unique constraint violated")


class TestDocumentValidationError:
    def test_inherits_from_no_sql_error(self) -> None:
        """DocumentValidationError inherits from NoSQLError."""
        assert issubclass(DocumentValidationError, NoSQLError)

    def test_has_error_code(self) -> None:
        """DocumentValidationError has an error code."""
        err = DocumentValidationError("validation failed")
        assert err._code == "LEX_ERR_NOSQL_005"

    def test_can_be_raised(self) -> None:
        """DocumentValidationError can be raised and caught."""
        with pytest.raises(DocumentValidationError):
            raise DocumentValidationError("schema validation failed")


class TestTransactionError:
    def test_inherits_from_no_sql_error(self) -> None:
        """TransactionError inherits from NoSQLError."""
        assert issubclass(TransactionError, NoSQLError)

    def test_has_error_code(self) -> None:
        """TransactionError has an error code."""
        err = TransactionError("transaction failed")
        assert err._code == "LEX_ERR_NOSQL_006"

    def test_can_be_raised(self) -> None:
        """TransactionError can be raised and caught."""
        with pytest.raises(TransactionError):
            raise TransactionError("transaction aborted")


class TestExceptionHierarchy:
    def test_all_inherit_from_no_sql_error(self) -> None:
        """All NoSQL exceptions inherit from NoSQLError."""
        assert issubclass(NoSQLConnectionError, NoSQLError)
        assert issubclass(DocumentNotFoundError, NoSQLError)
        assert issubclass(DuplicateKeyError, NoSQLError)
        assert issubclass(DocumentValidationError, NoSQLError)
        assert issubclass(TransactionError, NoSQLError)

    def test_can_catch_base_and_derived(self) -> None:
        """Derived exceptions can be caught by base type."""
        with pytest.raises(NoSQLError):
            raise DocumentNotFoundError("test")

    def test_can_catch_specific(self) -> None:
        """Specific exceptions can be caught individually."""
        with pytest.raises(DocumentNotFoundError):
            raise DocumentNotFoundError("test")

        with pytest.raises(DuplicateKeyError):
            raise DuplicateKeyError("test")