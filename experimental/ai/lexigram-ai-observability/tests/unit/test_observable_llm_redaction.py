"""Unit tests for ObservableLLMClient audit metadata redaction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.observability.wrappers.observable_llm import ObservableLLMClient
from lexigram.logging.redaction import DefaultRedactor


class TestEmitAuditRedaction:
    """Tests for _emit_audit metadata redaction."""

    @pytest.fixture
    def mock_delegate(self) -> MagicMock:
        """Return a mock LLMClientProtocol delegate."""
        delegate = MagicMock()
        delegate.complete = AsyncMock()
        delegate.stream_chat = MagicMock()
        delegate.health_check = AsyncMock()
        delegate.close = AsyncMock()
        return delegate

    @pytest.fixture
    def mock_audit_store(self) -> MagicMock:
        """Return a mock AIAuditStoreProtocol."""
        audit_store = MagicMock()
        audit_store.record = AsyncMock()
        return audit_store

    async def test_emit_audit_redacts_metadata_with_policy(
        self, mock_delegate: MagicMock, mock_audit_store: MagicMock
    ) -> None:
        """Test secret-shaped metadata keys are redacted before recording."""
        client = ObservableLLMClient(
            mock_delegate,
            provider="openai",
            model="gpt-4",
            audit_store=mock_audit_store,
            redaction_policy=DefaultRedactor(),
        )

        client._emit_audit(status="success", metadata={"api_key": "sk-123"})

        event = mock_audit_store.record.call_args[0][0]
        assert event.metadata == {"api_key": "<redacted>"}

    async def test_emit_audit_passes_metadata_through_without_policy(
        self, mock_delegate: MagicMock, mock_audit_store: MagicMock
    ) -> None:
        """Test metadata is unchanged when no policy is configured."""
        client = ObservableLLMClient(
            mock_delegate,
            provider="openai",
            model="gpt-4",
            audit_store=mock_audit_store,
        )

        client._emit_audit(status="success", metadata={"api_key": "sk-123"})

        event = mock_audit_store.record.call_args[0][0]
        assert event.metadata == {"api_key": "sk-123"}

    async def test_emit_audit_without_metadata_records_empty_bag(
        self, mock_delegate: MagicMock, mock_audit_store: MagicMock
    ) -> None:
        """Test metadata defaults to an empty dict when omitted."""
        client = ObservableLLMClient(
            mock_delegate,
            provider="openai",
            model="gpt-4",
            audit_store=mock_audit_store,
        )

        client._emit_audit(status="success")

        event = mock_audit_store.record.call_args[0][0]
        assert event.metadata == {}

    async def test_emit_audit_redacts_metadata_in_complete_error_path(
        self, mock_delegate: MagicMock, mock_audit_store: MagicMock
    ) -> None:
        """Test complete() error audits keep metadata-free events unchanged."""
        client = ObservableLLMClient(
            mock_delegate,
            provider="openai",
            model="gpt-4",
            audit_store=mock_audit_store,
            redaction_policy=DefaultRedactor(),
        )

        client._emit_audit(status="error", latency_ms=12.5)

        event = mock_audit_store.record.call_args[0][0]
        assert event.status == "error"
        assert event.metadata == {}
