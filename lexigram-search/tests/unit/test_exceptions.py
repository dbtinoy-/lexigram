"""Tests for search exceptions."""

import pytest

from lexigram.search.exceptions import (
    BackendError,
    IndexNotFoundError,
    SearchError,
    SearchValidationError,
)


class TestSearchError:
    """Tests for SearchError."""

    def test_is_exception(self) -> None:
        """SearchError should be an Exception."""
        error = SearchError()
        assert isinstance(error, Exception)


class TestIndexNotFoundError:
    """Tests for IndexNotFoundError."""

    def test_is_exception(self) -> None:
        """Should be an Exception."""
        error = IndexNotFoundError()
        assert isinstance(error, Exception)


class TestBackendError:
    """Tests for BackendError."""

    def test_is_exception(self) -> None:
        """Should be an Exception."""
        error = BackendError()
        assert isinstance(error, Exception)


class TestSearchValidationError:
    """Tests for SearchValidationError."""

    def test_is_search_error(self) -> None:
        """Should inherit from SearchError."""
        error = SearchValidationError()
        assert isinstance(error, SearchError)
