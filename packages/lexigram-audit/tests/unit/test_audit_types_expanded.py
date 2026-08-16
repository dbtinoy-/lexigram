"""Tests for audit types."""

from __future__ import annotations

from datetime import datetime

import pytest

from lexigram.audit.types import AuditStoreBackend, PurgeResult, VerificationResult


class TestAuditStoreBackend:
    """Tests for AuditStoreBackend enum."""

    def test_memory_value(self) -> None:
        assert AuditStoreBackend.MEMORY.value == "memory"

    def test_sql_value(self) -> None:
        assert AuditStoreBackend.SQL.value == "sql"

    def test_enum_values(self) -> None:
        values = [e.value for e in AuditStoreBackend]
        assert "memory" in values
        assert "sql" in values


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_creation(self) -> None:
        started = datetime.now()
        completed = datetime.now()
        result = VerificationResult(
            entries_checked=100,
            mismatches=0,
            started_at=started,
            completed_at=completed,
        )
        assert result.entries_checked == 100
        assert result.mismatches == 0

    def test_is_clean_true(self) -> None:
        result = VerificationResult(
            entries_checked=100,
            mismatches=0,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        assert result.is_clean is True

    def test_is_clean_false(self) -> None:
        result = VerificationResult(
            entries_checked=100,
            mismatches=5,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        assert result.is_clean is False

    def test_is_frozen(self) -> None:
        result = VerificationResult(
            entries_checked=100,
            mismatches=0,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        with pytest.raises(AttributeError):
            result.entries_checked = 200


class TestPurgeResult:
    """Tests for PurgeResult dataclass."""

    def test_creation_defaults(self) -> None:
        result = PurgeResult(entries_purged=10)
        assert result.entries_purged == 10
        assert result.entries_archived == 0
        assert result.entries_retained == 0

    def test_creation_with_all_fields(self) -> None:
        result = PurgeResult(
            entries_purged=10,
            entries_archived=5,
            entries_retained=85,
        )
        assert result.entries_purged == 10
        assert result.entries_archived == 5
        assert result.entries_retained == 85

    def test_is_frozen(self) -> None:
        result = PurgeResult(entries_purged=10)
        with pytest.raises(AttributeError):
            result.entries_purged = 20


class TestAuditTypesModuleExports:
    """Tests for module exports."""

    def test_all_contains_expected(self) -> None:
        from lexigram.audit import types
        expected = ["AuditStoreBackend", "PurgeResult", "VerificationResult"]
        for name in expected:
            assert hasattr(types, name)

    def test_all_exports_match(self) -> None:
        from lexigram.audit import types
        assert types.__all__ == ["AuditStoreBackend", "PurgeResult", "VerificationResult"]