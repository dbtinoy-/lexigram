"""Tests for storage exceptions."""

import pytest

from lexigram.storage.exceptions import StorageError


class TestStorageError:
    """Tests for StorageError."""

    def test_can_instantiate(self) -> None:
        """Should be able to create an error."""
        error = StorageError("test")
        assert "test" in str(error)
