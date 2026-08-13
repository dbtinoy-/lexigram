"""Tests for webhook constants module."""

from __future__ import annotations
from enum import Enum

import pytest

from lexigram.webhook.constants import (
    DEFAULT_DELIVERY_LOG_RETENTION_DAYS,
    DEFAULT_DELIVERY_TIMEOUT_SECONDS,
    DEFAULT_DISABLE_AFTER_CONSECUTIVE_FAILURES,
    DEFAULT_EVENT_ID_HEADER,
    DEFAULT_EVENT_TYPE_HEADER,
    DEFAULT_FAILURE_WINDOW_HOURS,
    DEFAULT_RETRY_BACKOFF_FACTOR,
    DEFAULT_RETRY_BASE_DELAY,
    DEFAULT_RETRY_MAX_ATTEMPTS,
    DEFAULT_RETRY_MAX_DELAY,
    DEFAULT_SECRET_LENGTH,
    DEFAULT_SECRET_ROTATION_GRACE_HOURS,
    DEFAULT_SIGNATURE_ALGORITHM,
    DEFAULT_SIGNATURE_HEADER,
    DEFAULT_STORE_BACKEND,
    DEFAULT_TIMESTAMP_HEADER,
    ENV_NESTED_DELIMITER,
    ENV_PREFIX,
    DeliveryStatus,
    SignatureAlgorithm,
    StoreBackend,
    __version__,
)


class TestVersion:
    """Tests for version constant."""

    def test_version_is_string(self) -> None:
        """Version is a string."""
        assert isinstance(__version__, str)

    def test_version_not_empty(self) -> None:
        """Version is not empty."""
        assert len(__version__) > 0


class TestEnvironmentConstants:
    """Tests for environment variable constants."""

    def test_env_prefix(self) -> None:
        """ENV_PREFIX has correct value."""
        assert ENV_PREFIX == "LEX_WEBHOOK__"

    def test_env_nested_delimiter(self) -> None:
        """ENV_NESTED_DELIMITER has correct value."""
        assert ENV_NESTED_DELIMITER == "__"


class TestDefaultConfigValues:
    """Tests for default configuration values."""

    def test_default_store_backend(self) -> None:
        assert DEFAULT_STORE_BACKEND == "memory"

    def test_default_retry_max_attempts(self) -> None:
        assert DEFAULT_RETRY_MAX_ATTEMPTS == 5

    def test_default_retry_base_delay(self) -> None:
        assert DEFAULT_RETRY_BASE_DELAY == 1.0

    def test_default_retry_max_delay(self) -> None:
        assert DEFAULT_RETRY_MAX_DELAY == 60.0

    def test_default_retry_backoff_factor(self) -> None:
        assert DEFAULT_RETRY_BACKOFF_FACTOR == 2.0

    def test_default_secret_length(self) -> None:
        assert DEFAULT_SECRET_LENGTH == 32

    def test_default_secret_rotation_grace_hours(self) -> None:
        assert DEFAULT_SECRET_ROTATION_GRACE_HOURS == 24

    def test_default_delivery_timeout_seconds(self) -> None:
        assert DEFAULT_DELIVERY_TIMEOUT_SECONDS == 30.0

    def test_default_disable_after_consecutive_failures(self) -> None:
        assert DEFAULT_DISABLE_AFTER_CONSECUTIVE_FAILURES == 50

    def test_default_failure_window_hours(self) -> None:
        assert DEFAULT_FAILURE_WINDOW_HOURS == 24

    def test_default_signature_algorithm(self) -> None:
        assert DEFAULT_SIGNATURE_ALGORITHM == "sha256"

    def test_default_delivery_log_retention_days(self) -> None:
        assert DEFAULT_DELIVERY_LOG_RETENTION_DAYS == 30

    def test_default_signature_header(self) -> None:
        assert DEFAULT_SIGNATURE_HEADER == "X-Webhook-Signature"

    def test_default_event_type_header(self) -> None:
        assert DEFAULT_EVENT_TYPE_HEADER == "X-Webhook-Event-Type"

    def test_default_event_id_header(self) -> None:
        assert DEFAULT_EVENT_ID_HEADER == "X-Webhook-Event-ID"

    def test_default_timestamp_header(self) -> None:
        assert DEFAULT_TIMESTAMP_HEADER == "X-Webhook-Timestamp"


class TestStoreBackendEnum:
    """Tests for StoreBackend StrEnum."""

    def test_store_backend_is_str_enum(self) -> None:
        """StoreBackend inherits from StrEnum."""
        from enum import StrEnum
        assert issubclass(StoreBackend, StrEnum)

    def test_store_backend_sql_value(self) -> None:
        """StoreBackend.SQL has correct value."""
        assert StoreBackend.SQL == "sql"

    def test_store_backend_memory_value(self) -> None:
        """StoreBackend.MEMORY has correct value."""
        assert StoreBackend.MEMORY == "memory"

    def test_store_backend_is_string(self) -> None:
        """StoreBackend members are strings."""
        assert isinstance(StoreBackend.SQL, str)
        assert isinstance(StoreBackend.MEMORY, str)

    def test_store_backend_values(self) -> None:
        """StoreBackend has expected values."""
        values = {e.value for e in StoreBackend}
        assert values == {"sql", "memory"}


class TestDeliveryStatusEnum:
    """Tests for DeliveryStatus StrEnum."""

    def test_delivery_status_is_str_enum(self) -> None:
        """DeliveryStatus inherits from StrEnum."""
        from enum import StrEnum
        assert issubclass(DeliveryStatus, StrEnum)

    def test_delivery_status_pending_value(self) -> None:
        """DeliveryStatus.PENDING has correct value."""
        assert DeliveryStatus.PENDING == "pending"

    def test_delivery_status_delivered_value(self) -> None:
        """DeliveryStatus.DELIVERED has correct value."""
        assert DeliveryStatus.DELIVERED == "delivered"

    def test_delivery_status_failed_value(self) -> None:
        """DeliveryStatus.FAILED has correct value."""
        assert DeliveryStatus.FAILED == "failed"

    def test_delivery_status_dead_letter_value(self) -> None:
        """DeliveryStatus.DEAD_LETTER has correct value."""
        assert DeliveryStatus.DEAD_LETTER == "dead_letter"

    def test_delivery_status_is_string(self) -> None:
        """DeliveryStatus members are strings."""
        for status in DeliveryStatus:
            assert isinstance(status, str)

    def test_delivery_status_values(self) -> None:
        """DeliveryStatus has expected values."""
        values = {e.value for e in DeliveryStatus}
        assert values == {"pending", "delivered", "failed", "dead_letter"}


class TestSignatureAlgorithmEnum:
    """Tests for SignatureAlgorithm StrEnum."""

    def test_signature_algorithm_is_str_enum(self) -> None:
        """SignatureAlgorithm inherits from StrEnum."""
        from enum import StrEnum
        assert issubclass(SignatureAlgorithm, StrEnum)

    def test_signature_algorithm_sha256_value(self) -> None:
        """SignatureAlgorithm.SHA256 has correct value."""
        assert SignatureAlgorithm.SHA256 == "sha256"

    def test_signature_algorithm_sha512_value(self) -> None:
        """SignatureAlgorithm.SHA512 has correct value."""
        assert SignatureAlgorithm.SHA512 == "sha512"

    def test_signature_algorithm_is_string(self) -> None:
        """SignatureAlgorithm members are strings."""
        assert isinstance(SignatureAlgorithm.SHA256, str)
        assert isinstance(SignatureAlgorithm.SHA512, str)

    def test_signature_algorithm_values(self) -> None:
        """SignatureAlgorithm has expected values."""
        values = {e.value for e in SignatureAlgorithm}
        assert values == {"sha256", "sha512"}


class TestAllExports:
    """Tests for __all__ exports."""

    def test_all_contains_expected_items(self) -> None:
        """__all__ contains all expected exports."""
        from lexigram.webhook import constants
        expected = [
            "ENV_NESTED_DELIMITER",
            "ENV_PREFIX",
            "DEFAULT_DELIVERY_LOG_RETENTION_DAYS",
            "DEFAULT_DELIVERY_TIMEOUT_SECONDS",
            "DEFAULT_DISABLE_AFTER_CONSECUTIVE_FAILURES",
            "DEFAULT_EVENT_ID_HEADER",
            "DEFAULT_EVENT_TYPE_HEADER",
            "DEFAULT_FAILURE_WINDOW_HOURS",
            "DEFAULT_RETRY_BACKOFF_FACTOR",
            "DEFAULT_RETRY_BASE_DELAY",
            "DEFAULT_RETRY_MAX_ATTEMPTS",
            "DEFAULT_RETRY_MAX_DELAY",
            "DEFAULT_SECRET_LENGTH",
            "DEFAULT_SECRET_ROTATION_GRACE_HOURS",
            "DEFAULT_SIGNATURE_ALGORITHM",
            "DEFAULT_SIGNATURE_HEADER",
            "DEFAULT_STORE_BACKEND",
            "DEFAULT_TIMESTAMP_HEADER",
            "DeliveryStatus",
            "SignatureAlgorithm",
            "StoreBackend",
            "__version__",
        ]
        for item in expected:
            assert item in constants.__all__
