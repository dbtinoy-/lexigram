"""Tests for database full-text search types."""

import pytest

from lexigram.sql.search.full_text import FTSResult, FTSDialect


class TestFTSDialect:
    """Tests for FTSDialect enum."""

    def test_fts_dialect_values(self) -> None:
        """Test FTSDialect enum values."""
        assert FTSDialect.POSTGRES.value == "postgres"
        assert FTSDialect.MYSQL.value == "mysql"

    def test_fts_dialect_members(self) -> None:
        """Test FTSDialect has expected members."""
        members = list(FTSDialect)
        assert len(members) == 2


class TestFTSResult:
    """Tests for FTSResult dataclass."""

    def test_fts_result_creation(self) -> None:
        """Test FTSResult creation."""
        result = FTSResult(
            items=["item1", "item2"],
            total=10,
            dialect=FTSDialect.POSTGRES,
        )
        assert result.items == ["item1", "item2"]
        assert result.total == 10
        assert result.dialect == FTSDialect.POSTGRES

    def test_fts_result_iteration(self) -> None:
        """Test FTSResult iteration."""
        result = FTSResult(
            items=["a", "b", "c"],
            total=3,
            dialect=FTSDialect.MYSQL,
        )
        assert list(result) == ["a", "b", "c"]

    def test_fts_result_length(self) -> None:
        """Test FTSResult length."""
        result = FTSResult(
            items=["a", "b"],
            total=5,
            dialect=FTSDialect.POSTGRES,
        )
        assert len(result) == 2
