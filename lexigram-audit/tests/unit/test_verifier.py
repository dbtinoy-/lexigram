"""Tests for AuditVerifier."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.audit.verification.verifier import AuditVerifier
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity


class MockConfig:
    """Mock config for testing."""

    def __init__(self, hmac_key: str | None = "test-key") -> None:
        self.hmac_key = hmac_key.encode() if hmac_key else None


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
    async def test_verify_entry_returns_true(self, mock_store, mock_config_with_key) -> None:
        verifier = AuditVerifier(store=mock_store, config=mock_config_with_key)
        result = await verifier.verify_entry("entry-123")
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_entry_no_key_returns_true(self, mock_store, mock_config_no_key) -> None:
        verifier = AuditVerifier(store=mock_store, config=mock_config_no_key)
        result = await verifier.verify_entry("entry-123")
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_recent_with_entries(self, mock_config_with_key) -> None:
        entries = [
            AuditEntry(action="test", actor_id="u", outcome="success")
            for _ in range(5)
        ]
        store = MagicMock()
        store.query = AsyncMock(return_value=entries)
        
        verifier = AuditVerifier(store=store, config=mock_config_with_key)
        result = await verifier.verify_recent()
        
        assert result == []
        assert store.query.call_count == 1