from __future__ import annotations

import pytest


class TestVersion:
    """Tests for version constant."""

    def test_version_is_string(self) -> None:
        from lexigram.audit.constants import __version__
        assert isinstance(__version__, str)

    def test_version_format(self) -> None:
        from lexigram.audit.constants import __version__
        parts = __version__.split(".")
        assert len(parts) >= 3


class TestEnvironmentConstants:
    """Tests for environment variable constants."""

    def test_env_prefix(self) -> None:
        from lexigram.audit.constants import ENV_PREFIX
        assert ENV_PREFIX == "LEX_AUDIT__"

    def test_env_nested_delimiter(self) -> None:
        from lexigram.audit.constants import ENV_NESTED_DELIMITER
        assert ENV_NESTED_DELIMITER == "__"


class TestDefaultConfigValues:
    """Tests for default configuration values."""

    def test_default_store_backend(self) -> None:
        from lexigram.audit.constants import DEFAULT_STORE_BACKEND
        assert DEFAULT_STORE_BACKEND == "sql"

    def test_default_table_name(self) -> None:
        from lexigram.audit.constants import DEFAULT_TABLE_NAME
        assert DEFAULT_TABLE_NAME == "audit_log"

    def test_default_verification_schedule(self) -> None:
        from lexigram.audit.constants import DEFAULT_VERIFICATION_SCHEDULE
        assert DEFAULT_VERIFICATION_SCHEDULE == "0 * * * *"

    def test_default_verification_batch_size(self) -> None:
        from lexigram.audit.constants import DEFAULT_VERIFICATION_BATCH_SIZE
        assert DEFAULT_VERIFICATION_BATCH_SIZE == 100


class TestStoreBackendEnum:
    """Tests for StoreBackend StrEnum."""

    def test_sql_value(self) -> None:
        from lexigram.audit.constants import StoreBackend
        assert StoreBackend.SQL == "sql"

    def test_memory_value(self) -> None:
        from lexigram.audit.constants import StoreBackend
        assert StoreBackend.MEMORY == "memory"

    def test_enum_is_str(self) -> None:
        from lexigram.audit.constants import StoreBackend
        assert isinstance(StoreBackend.SQL, str)

    def test_all_backends(self) -> None:
        from lexigram.audit.constants import StoreBackend
        assert len(StoreBackend) == 2


class TestAuditSeverityEnum:
    """Tests for AuditSeverity StrEnum."""

    def test_low_value(self) -> None:
        from lexigram.audit.constants import AuditSeverity
        assert AuditSeverity.LOW == "low"

    def test_medium_value(self) -> None:
        from lexigram.audit.constants import AuditSeverity
        assert AuditSeverity.MEDIUM == "medium"

    def test_high_value(self) -> None:
        from lexigram.audit.constants import AuditSeverity
        assert AuditSeverity.HIGH == "high"

    def test_critical_value(self) -> None:
        from lexigram.audit.constants import AuditSeverity
        assert AuditSeverity.CRITICAL == "critical"

    def test_enum_is_str(self) -> None:
        from lexigram.audit.constants import AuditSeverity
        assert isinstance(AuditSeverity.LOW, str)

    def test_all_severities(self) -> None:
        from lexigram.audit.constants import AuditSeverity
        assert len(AuditSeverity) == 4


class TestAuditOutcomeEnum:
    """Tests for AuditOutcome StrEnum."""

    def test_success_value(self) -> None:
        from lexigram.audit.constants import AuditOutcome
        assert AuditOutcome.SUCCESS == "success"

    def test_failure_value(self) -> None:
        from lexigram.audit.constants import AuditOutcome
        assert AuditOutcome.FAILURE == "failure"

    def test_partial_value(self) -> None:
        from lexigram.audit.constants import AuditOutcome
        assert AuditOutcome.PARTIAL == "partial"

    def test_unknown_value(self) -> None:
        from lexigram.audit.constants import AuditOutcome
        assert AuditOutcome.UNKNOWN == "unknown"

    def test_enum_is_str(self) -> None:
        from lexigram.audit.constants import AuditOutcome
        assert isinstance(AuditOutcome.SUCCESS, str)

    def test_all_outcomes(self) -> None:
        from lexigram.audit.constants import AuditOutcome
        assert len(AuditOutcome) == 4