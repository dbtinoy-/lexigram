"""Tests for admin GDPR types."""

import pytest

from lexigram.admin.gdpr import AnonymizationStrategy, SARStatus


class TestAnonymizationStrategy:
    """Tests for AnonymizationStrategy enum."""

    def test_anonymization_strategy_values(self) -> None:
        """Test AnonymizationStrategy enum values."""
        assert AnonymizationStrategy.HASH.value == "hash"
        assert AnonymizationStrategy.CLEAR.value == "clear"
        assert AnonymizationStrategy.REDACT.value == "redact"
        assert AnonymizationStrategy.ZERO.value == "zero"
        assert AnonymizationStrategy.NULLIFY.value == "nullify"
        assert AnonymizationStrategy.FAKE_EMAIL.value == "fake_email"

    def test_anonymization_strategy_members(self) -> None:
        """Test AnonymizationStrategy has expected members."""
        members = list(AnonymizationStrategy)
        assert len(members) == 6


class TestSARStatus:
    """Tests for SARStatus enum."""

    def test_sar_status_values(self) -> None:
        """Test SARStatus enum values."""
        assert SARStatus.PENDING.value == "pending"
        assert SARStatus.IN_PROGRESS.value == "in_progress"
        assert SARStatus.COMPLETED.value == "completed"
        assert SARStatus.REJECTED.value == "rejected"

    def test_sar_status_members(self) -> None:
        """Test SARStatus has expected members."""
        members = list(SARStatus)
        assert len(members) == 4
