"""Tests for idempotency types and configuration."""

from datetime import UTC, datetime, timedelta

from lexigram.contracts.domain.idempotency import IdempotencyRecord, IdempotencyStatus
from lexigram.resilience.config import IdempotencyConfig


class TestIdempotencyStatus:
    """Tests for IdempotencyStatus enum."""

    def test_status_values(self) -> None:
        """Test all status values exist."""
        assert IdempotencyStatus.PENDING is not None
        assert IdempotencyStatus.COMPLETE is not None
        assert IdempotencyStatus.EXPIRED is not None


class TestIdempotencyRecord:
    """Tests for IdempotencyRecord dataclass."""

    def test_record_creation(self) -> None:
        """Test creating an idempotency record."""
        now = datetime.now(UTC)
        record = IdempotencyRecord(
            key="test-key",
            result={"data": "value"},
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        assert record.key == "test-key"
        assert record.result == {"data": "value"}
        assert record.status == IdempotencyStatus.PENDING

    def test_record_with_complete_status(self) -> None:
        """Test record with COMPLETE status."""
        now = datetime.now(UTC)
        record = IdempotencyRecord(
            key="test-key",
            result="completed",
            created_at=now,
            expires_at=now + timedelta(hours=1),
            status=IdempotencyStatus.COMPLETE,
        )
        assert record.status == IdempotencyStatus.COMPLETE

    def test_record_with_expired_status(self) -> None:
        """Test record with EXPIRED status."""
        now = datetime.now(UTC)
        record = IdempotencyRecord(
            key="test-key",
            result=None,
            created_at=now,
            expires_at=now - timedelta(hours=1),
            status=IdempotencyStatus.EXPIRED,
        )
        assert record.status == IdempotencyStatus.EXPIRED

    def test_record_default_status(self) -> None:
        """Test that default status is PENDING."""
        now = datetime.now(UTC)
        record = IdempotencyRecord(
            key="test-key",
            result="test",
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        assert record.status == IdempotencyStatus.PENDING


class TestIdempotencyConfig:
    """Tests for IdempotencyConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = IdempotencyConfig()
        assert config.ttl == 3600  # 1 hour
        assert config.max_entries == 10000
        assert config.cleanup_interval == 300.0
        assert config.auto_cleanup is True
        assert config.key_prefix == "idempotency:"
        assert config.max_key_length == 512

    def test_custom_ttl(self) -> None:
        """Test configuring custom TTL."""
        config = IdempotencyConfig(ttl=3600)
        assert config.ttl == 3600

    def test_custom_max_entries(self) -> None:
        """Test configuring custom max entries."""
        config = IdempotencyConfig(max_entries=5000)
        assert config.max_entries == 5000

    def test_custom_cleanup_interval(self) -> None:
        """Test configuring custom cleanup interval."""
        config = IdempotencyConfig(cleanup_interval=1800.0)
        assert config.cleanup_interval == 1800.0

    def test_disable_auto_cleanup(self) -> None:
        """Test disabling auto cleanup."""
        config = IdempotencyConfig(auto_cleanup=False)
        assert config.auto_cleanup is False

    def test_custom_key_prefix(self) -> None:
        """Test configuring custom key prefix."""
        config = IdempotencyConfig(key_prefix="custom:")
        assert config.key_prefix == "custom:"

    def test_custom_max_key_length(self) -> None:
        """Test configuring custom max key length."""
        config = IdempotencyConfig(max_key_length=128)
        assert config.max_key_length == 128
