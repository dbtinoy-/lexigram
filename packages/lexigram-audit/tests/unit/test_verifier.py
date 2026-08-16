"""Tests for AuditVerifier."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.audit.store.sql import entry_to_row
from lexigram.audit.verification.checksum import compute_audit_checksum
from lexigram.audit.verification.verifier import AuditVerifier
from lexigram.contracts.audit import (
    AuditEntry,
    AuditEventSeverity,
    AuditMismatchReason,
)


class MockConfig:
    """Mock config for testing."""

    def __init__(self, hmac_key: str | None = "test-key") -> None:
        self.hmac_key = hmac_key.encode() if hmac_key else None


def _entry(**kw: Any) -> AuditEntry:
    base: dict[str, Any] = {
        "action": "user.login",
        "actor_id": "u-1",
        "resource_type": "User",
        "resource_id": "u-1",
        "outcome": "success",
        "severity": AuditEventSeverity.MEDIUM,
        "source": "admin",
    }
    base.update(kw)
    return AuditEntry(**base)


def _checksum(entry: AuditEntry, key: bytes, schema_version: int = 2) -> str:
    return compute_audit_checksum(entry_to_row(entry), key, schema_version=schema_version)


def _signed(entry: AuditEntry, key: bytes, schema_version: int = 2) -> AuditEntry:
    """Return the entry with a valid checksum over its own row."""
    return replace(entry, checksum=_checksum(entry, key, schema_version))


class TestAuditVerifier:
    """Tests for AuditVerifier."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        store = MagicMock()
        store.query = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def mock_config_with_key(self) -> MockConfig:
        return MockConfig(hmac_key="test-secret-key")

    @pytest.fixture
    def mock_config_no_key(self) -> MockConfig:
        return MockConfig(hmac_key=None)

    def test_verifier_creation_with_key(self, mock_store, mock_config_with_key) -> None:
        verifier = AuditVerifier(store=mock_store, config=mock_config_with_key)
        assert verifier._hmac_key is not None

    def test_verifier_creation_without_key(self, mock_store, mock_config_no_key) -> None:
        verifier = AuditVerifier(store=mock_store, config=mock_config_no_key)
        assert verifier._hmac_key is None

    @pytest.mark.asyncio
    async def test_verify_recent_no_key_returns_empty(self, mock_store, mock_config_no_key) -> None:
        verifier = AuditVerifier(store=mock_store, config=mock_config_no_key)
        result = await verifier.verify_recent()
        assert result == []
        mock_store.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_verify_recent_with_key_queries_store(self, mock_store, mock_config_with_key) -> None:
        verifier = AuditVerifier(store=mock_store, config=mock_config_with_key)
        result = await verifier.verify_recent(limit=50)
        assert result == []
        mock_store.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_recent_uses_limit_param(self, mock_store, mock_config_with_key) -> None:
        verifier = AuditVerifier(store=mock_store, config=mock_config_with_key)
        await verifier.verify_recent(limit=200)

        call_args = mock_store.query.call_args
        query = call_args[0][0]
        assert query.limit == 200

    @pytest.mark.asyncio
    async def test_verify_entry_no_key_returns_none(self, mock_store, mock_config_no_key) -> None:
        verifier = AuditVerifier(store=mock_store, config=mock_config_no_key)
        result = await verifier.verify_entry(_entry())
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_entry_clean_returns_none(self, mock_store, mock_config_with_key) -> None:
        entry = _signed(_entry(), b"test-secret-key")
        verifier = AuditVerifier(store=mock_store, config=mock_config_with_key)
        result = await verifier.verify_entry(entry)
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_entry_tampered_returns_mismatch(self, mock_store, mock_config_with_key) -> None:
        entry = _entry(checksum="0" * 64)
        verifier = AuditVerifier(store=mock_store, config=mock_config_with_key)
        result = await verifier.verify_entry(entry)
        assert result is not None
        assert result.reason == AuditMismatchReason.CHECKSUM_MISMATCH
        assert result.expected_checksum == "0" * 64
        assert result.actual_checksum != result.expected_checksum

    @pytest.mark.asyncio
    async def test_verify_entry_legacy_no_checksum_reports_unverifiable(
        self, mock_store, mock_config_with_key
    ) -> None:
        entry = _entry()
        assert entry.checksum is None
        verifier = AuditVerifier(store=mock_store, config=mock_config_with_key)
        result = await verifier.verify_entry(entry)
        assert result is not None
        assert result.reason == AuditMismatchReason.NO_CHECKSUM_PRESENT
        assert result.expected_checksum == ""

    @pytest.mark.asyncio
    async def test_verify_entry_accepts_v1_checksum(self, mock_store, mock_config_with_key) -> None:
        entry = _signed(_entry(), b"test-secret-key", schema_version=1)
        verifier = AuditVerifier(store=mock_store, config=mock_config_with_key)
        result = await verifier.verify_entry(entry)
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_recent_with_entries(self, mock_config_with_key) -> None:
        key = b"test-secret-key"
        entries = [_signed(_entry(action=f"act.{i}"), key) for i in range(5)]
        store = MagicMock()
        store.query = AsyncMock(return_value=entries)

        verifier = AuditVerifier(store=store, config=mock_config_with_key)
        result = await verifier.verify_recent()

        assert result == []
        assert store.query.call_count == 1

    @pytest.mark.asyncio
    async def test_verify_recent_collects_all_mismatch_kinds(self, mock_config_with_key) -> None:
        key = b"test-secret-key"
        clean = _signed(_entry(action="a.clean"), key)
        tampered = _entry(action="b.tampered", checksum="1" * 64)
        legacy = _entry(action="c.legacy", checksum=None)
        entries = [clean, tampered, legacy]
        store = MagicMock()
        store.query = AsyncMock(return_value=entries)

        verifier = AuditVerifier(store=store, config=mock_config_with_key)
        result = await verifier.verify_recent()

        assert len(result) == 2
        reasons = {m.reason for m in result}
        assert reasons == {
            AuditMismatchReason.CHECKSUM_MISMATCH,
            AuditMismatchReason.NO_CHECKSUM_PRESENT,
        }
