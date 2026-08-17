"""Tests for core/resilience_config.py — AuditEntry, InMemoryAuditLogger, AuditRepositoryMixin."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.core.resilience_config import (
    AuditEntry,
    AuditRepositoryMixin,
    InMemoryAuditLogger,
)


class TestAuditEntry:
    """Tests for AuditEntry dataclass."""

    def test_required_fields(self) -> None:
        entry = AuditEntry(
            action="create",
            resource_type="users",
            resource_id="user-1",
            user_id="admin-1",
        )
        assert entry.action == "create"
        assert entry.resource_type == "users"
        assert entry.resource_id == "user-1"
        assert entry.user_id == "admin-1"
        assert entry.changes is None
        assert entry.metadata is None

    def test_timestamp_defaults_to_now(self) -> None:
        before = datetime.now(UTC)
        entry = AuditEntry(
            action="delete",
            resource_type="posts",
            resource_id=42,
            user_id="admin",
        )
        after = datetime.now(UTC)
        assert before <= entry.timestamp <= after

    def test_with_changes(self) -> None:
        entry = AuditEntry(
            action="update",
            resource_type="users",
            resource_id="u1",
            user_id="a1",
            changes={"email": "new@example.com"},
        )
        assert entry.changes == {"email": "new@example.com"}

    def test_with_metadata(self) -> None:
        entry = AuditEntry(
            action="export",
            resource_type="reports",
            resource_id="r1",
            user_id="a1",
            metadata={"format": "csv"},
        )
        assert entry.metadata == {"format": "csv"}


class TestInMemoryAuditLogger:
    """Tests for InMemoryAuditLogger."""

    @pytest.mark.asyncio
    async def test_log_stores_entry(self) -> None:
        logger = InMemoryAuditLogger()
        await logger.log(
            action="create",
            resource_type="users",
            resource_id="u1",
            user_id="admin",
        )
        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0].action == "create"

    @pytest.mark.asyncio
    async def test_log_multiple_entries(self) -> None:
        logger = InMemoryAuditLogger()
        for i in range(3):
            await logger.log(
                action="view",
                resource_type="posts",
                resource_id=f"post-{i}",
                user_id="admin",
            )
        assert len(logger.get_entries()) == 3

    @pytest.mark.asyncio
    async def test_get_entries_filter_by_resource_type(self) -> None:
        logger = InMemoryAuditLogger()
        await logger.log("create", "users", "u1", "admin")
        await logger.log("create", "posts", "p1", "admin")
        await logger.log("update", "users", "u2", "admin")

        user_entries = logger.get_entries(resource_type="users")
        assert len(user_entries) == 2
        assert all(e.resource_type == "users" for e in user_entries)

    @pytest.mark.asyncio
    async def test_get_entries_filter_by_resource_id(self) -> None:
        logger = InMemoryAuditLogger()
        await logger.log("create", "users", "u1", "admin")
        await logger.log("update", "users", "u1", "admin")
        await logger.log("delete", "users", "u2", "admin")

        u1_entries = logger.get_entries(resource_id="u1")
        assert len(u1_entries) == 2

    @pytest.mark.asyncio
    async def test_get_entries_filter_by_action(self) -> None:
        logger = InMemoryAuditLogger()
        await logger.log("create", "users", "u1", "admin")
        await logger.log("update", "users", "u1", "admin")
        await logger.log("create", "posts", "p1", "admin")

        create_entries = logger.get_entries(action="create")
        assert len(create_entries) == 2

    @pytest.mark.asyncio
    async def test_get_entries_no_filter(self) -> None:
        logger = InMemoryAuditLogger()
        await logger.log("create", "users", "u1", "admin")
        await logger.log("delete", "posts", "p1", "admin")
        assert len(logger.get_entries()) == 2

    @pytest.mark.asyncio
    async def test_get_entries_combined_filters(self) -> None:
        logger = InMemoryAuditLogger()
        await logger.log("create", "users", "u1", "admin")
        await logger.log("update", "users", "u1", "admin")
        await logger.log("create", "users", "u2", "admin")

        entries = logger.get_entries(resource_type="users", resource_id="u1", action="create")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_log_with_changes_and_metadata(self) -> None:
        logger = InMemoryAuditLogger()
        await logger.log(
            action="update",
            resource_type="settings",
            resource_id="s1",
            user_id="admin",
            changes={"value": "new"},
            metadata={"ip": "127.0.0.1"},
        )
        entries = logger.get_entries()
        assert entries[0].changes == {"value": "new"}
        assert entries[0].metadata == {"ip": "127.0.0.1"}


class TestAuditRepositoryMixin:
    """Tests for AuditRepositoryMixin."""

    @pytest.mark.asyncio
    async def test_audit_create_with_logger(self) -> None:
        mixin: AuditRepositoryMixin = AuditRepositoryMixin()
        mixin.resource_type = "users"

        mock_logger = AsyncMock()
        mixin.set_audit_logger(mock_logger)

        record = MagicMock()
        record.id = "rec-1"
        user = MagicMock()
        user.id = "admin-1"

        await mixin._audit_create(record, user)
        mock_logger.log.assert_called_once_with(
            action="create",
            resource_type="users",
            resource_id="rec-1",
            user_id="admin-1",
            changes={"created": True},
        )

    @pytest.mark.asyncio
    async def test_audit_create_without_logger_is_noop(self) -> None:
        mixin: AuditRepositoryMixin = AuditRepositoryMixin()
        record = MagicMock()
        record.id = "r1"
        # No logger set — should not raise
        await mixin._audit_create(record, None)

    @pytest.mark.asyncio
    async def test_audit_update_with_logger(self) -> None:
        mixin: AuditRepositoryMixin = AuditRepositoryMixin()
        mixin.resource_type = "posts"

        mock_logger = AsyncMock()
        mixin.set_audit_logger(mock_logger)

        record = MagicMock()
        record.id = "post-1"
        user = MagicMock()
        user.id = "editor"

        await mixin._audit_update(record, {"title": "new"}, user)
        mock_logger.log.assert_called_once_with(
            action="update",
            resource_type="posts",
            resource_id="post-1",
            user_id="editor",
            changes={"title": "new"},
        )

    @pytest.mark.asyncio
    async def test_audit_delete_with_logger(self) -> None:
        mixin: AuditRepositoryMixin = AuditRepositoryMixin()
        mixin.resource_type = "comments"

        mock_logger = AsyncMock()
        mixin.set_audit_logger(mock_logger)

        user = MagicMock()
        user.id = "admin"

        await mixin._audit_delete("comment-99", user)
        mock_logger.log.assert_called_once_with(
            action="delete",
            resource_type="comments",
            resource_id="comment-99",
            user_id="admin",
        )

    @pytest.mark.asyncio
    async def test_audit_bulk_action_with_logger(self) -> None:
        mixin: AuditRepositoryMixin = AuditRepositoryMixin()
        mixin.resource_type = "tags"

        mock_logger = AsyncMock()
        mixin.set_audit_logger(mock_logger)

        user = MagicMock()
        user.id = "admin"

        await mixin._audit_bulk_action("delete", ["t1", "t2"], user, metadata={"reason": "cleanup"})
        mock_logger.log.assert_called_once_with(
            action="bulk_delete",
            resource_type="tags",
            resource_id=["t1", "t2"],
            user_id="admin",
            metadata={"reason": "cleanup"},
        )

    @pytest.mark.asyncio
    async def test_audit_create_user_none(self) -> None:
        mixin: AuditRepositoryMixin = AuditRepositoryMixin()
        mixin.resource_type = "items"

        mock_logger = AsyncMock()
        mixin.set_audit_logger(mock_logger)

        record = MagicMock()
        record.id = "item-1"

        # user=None → user_id should be None
        await mixin._audit_create(record, None)
        call_kwargs = mock_logger.log.call_args[1]
        assert call_kwargs["user_id"] is None

    @pytest.mark.asyncio
    async def test_audit_delete_without_logger_is_noop(self) -> None:
        mixin: AuditRepositoryMixin = AuditRepositoryMixin()
        # Should not raise even without logger
        await mixin._audit_delete("id-1", None)

    @pytest.mark.asyncio
    async def test_audit_bulk_action_without_logger_is_noop(self) -> None:
        mixin: AuditRepositoryMixin = AuditRepositoryMixin()
        await mixin._audit_bulk_action("update", ["x"], None)
