"""Tests for LLMAuditBridge (LXF-003)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.audit.query import AuditQueryService
from lexigram.audit.store.memory import InMemoryAuditStore
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity


class TestLLMAuditBridge:
    """Tests for LLMAuditBridge."""

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        logger = MagicMock()
        logger.log = AsyncMock()
        return logger

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        ctx = MagicMock()
        ctx.get_tenant_id = MagicMock(return_value="tenant-1")
        ctx.get_correlation_id = MagicMock(return_value="corr-abc")
        ctx.get_actor_id = MagicMock(return_value="service-1")
        return ctx

    @pytest.fixture
    def bridge(self, mock_logger: MagicMock, mock_context: MagicMock):
        from lexigram.ai.llm.audit_bridge import LLMAuditBridge
        return LLMAuditBridge(audit_logger=mock_logger, ctx=mock_context)

    @pytest.mark.asyncio
    async def test_on_completion_logs_audit_entry(self, bridge, mock_logger: MagicMock) -> None:
        from lexigram.ai.llm.types import Completion

        completion = Completion(
            content="Hello world",
            model="gpt-4",
            provider="openai",
            model_revision="2026-01-01",
            prompt_hash=b"abcdef1234567890",
            completion_tokens=10,
            prompt_tokens=50,
            request_id="req-123",
        )

        await bridge.on_completion(completion)

        mock_logger.log.assert_awaited_once()
        entry = mock_logger.log.call_args[0][0]
        assert isinstance(entry, AuditEntry)
        assert entry.action == "lexigram.llm.completion"
        assert entry.actor_id == "service-1"
        assert entry.tenant_id == "tenant-1"
        assert entry.correlation_id == "corr-abc"
        assert entry.command_payload_hash == b"abcdef1234567890"
        assert entry.payload_size_bytes == 50 * 4  # prompt_tokens * 4
        assert entry.severity == AuditEventSeverity.LOW
        assert entry.resource_type == "llm.completion"
        assert entry.resource_id == "req-123"

    @pytest.mark.asyncio
    async def test_on_completion_includes_metadata(self, bridge, mock_logger: MagicMock) -> None:
        from lexigram.ai.llm.types import Completion

        completion = Completion(
            content="Hello",
            model="gpt-4",
            provider="openai",
            model_revision="2026-01-01",
            prompt_hash=b"hash",
            completion_tokens=10,
            prompt_tokens=20,
            request_id="req-456",
        )

        await bridge.on_completion(completion)

        entry = mock_logger.log.call_args[0][0]
        assert entry.metadata["provider"] == "openai"
        assert entry.metadata["model"] == "gpt-4"
        assert entry.metadata["model_revision"] == "2026-01-01"
        assert entry.metadata["completion_tokens"] == 10
        assert entry.metadata["prompt_tokens"] == 20
