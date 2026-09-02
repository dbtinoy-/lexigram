"""Email delivery log tests (R46, docs/09-01-2026/42-email-delivery-log.md).

Covers the ``AdminEmailLogSqlStore`` (schema, record, list, prune, LIMIT
guard, truncation) and the ``AdminNotificationService`` hook (records
success/failure, swallows log errors, logs disabled types, skips
preference-filtered recipients).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from lexigram.admin.services.notifications.delivery_log_sql import (
    AdminEmailLogSqlStore,
)
from lexigram.admin.services.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationRecipient,
    NotificationType,
)
from lexigram.admin.services.notifications.service import AdminNotificationService


class FakeProvider:
    """Records calls; returns configurable query rows (store-test pattern)."""

    def __init__(self, rows: list[dict] | None = None) -> None:
        self.database_type = "sqlite"
        self.executed: list[tuple[str, list]] = []
        self.queries: list[tuple[str, list]] = []
        self._rows = rows or []

    async def execute(self, sql: str, params: list | None = None) -> object:
        self.executed.append((sql, list(params or [])))
        return SimpleNamespace(row_count=0)

    async def execute_query(self, sql: str, params: list | None = None) -> list[dict]:
        self.queries.append((sql, list(params or [])))
        return self._rows


class TestStore:
    @pytest.mark.asyncio
    async def test_ensure_schema_is_idempotent(self) -> None:
        provider = FakeProvider()
        store = AdminEmailLogSqlStore(provider)

        await store.ensure_schema()
        await store.ensure_schema()

        creates = [s for s, _ in provider.executed if "CREATE TABLE" in s]
        assert len(creates) == 1
        assert any("CREATE INDEX" in s for s, _ in provider.executed)

    @pytest.mark.asyncio
    async def test_record_inserts_and_prunes(self) -> None:
        provider = FakeProvider()
        store = AdminEmailLogSqlStore(provider)

        await store.record(
            notification_type="test_email",
            recipient="a@example.com",
            subject="Hello",
            success=True,
        )

        insert_sql, params = next(
            (s, p) for s, p in provider.executed if "INSERT INTO" in s
        )
        assert "admin_email_log" in insert_sql
        assert params[1:5] == ["test_email", "a@example.com", "Hello", True]
        assert params[5] is None
        assert any("DELETE FROM admin_email_log" in s for s, _ in provider.executed)

    @pytest.mark.asyncio
    async def test_record_truncates_long_fields(self) -> None:
        provider = FakeProvider()
        store = AdminEmailLogSqlStore(provider)

        await store.record(
            notification_type="x" * 100,
            recipient="a@example.com",
            subject="s" * 400,
            success=False,
            error="e" * 900,
        )

        _, params = next((s, p) for s, p in provider.executed if "INSERT INTO" in s)
        assert len(params[1]) == 64
        assert len(params[3]) == 255
        assert len(params[5]) == 500

    @pytest.mark.asyncio
    async def test_list_recent_orders_and_limits(self) -> None:
        provider = FakeProvider(
            rows=[
                {
                    "notification_type": "test_email",
                    "recipient": "a@example.com",
                    "subject": "Hello",
                    "success": 1,
                    "error": None,
                    "created_at": "2026-09-02 10:00:00",
                }
            ]
        )
        store = AdminEmailLogSqlStore(provider)

        rows = await store.list_recent(limit=25)

        sql, params = provider.queries[-1]
        assert "ORDER BY created_at DESC" in sql
        assert "LIMIT 25" in sql
        assert params == []
        assert rows == [dict(provider._rows[0])]

    @pytest.mark.asyncio
    async def test_limit_injection_raises(self) -> None:
        store = AdminEmailLogSqlStore(FakeProvider())

        with pytest.raises((ValueError, TypeError)):
            await store.list_recent(limit="25; DROP TABLE admin_email_log")  # type: ignore[arg-type]
        with pytest.raises((ValueError, TypeError)):
            await store.prune(keep="10; DROP TABLE x")  # type: ignore[arg-type]


def _notification(**overrides: object) -> Notification:
    defaults: dict = {
        "type": NotificationType.SYSTEM_ALERT,
        "subject": "Test subject",
        "body": "Body",
        "recipients": [NotificationRecipient(email="a@example.com")],
        "channels": [NotificationChannel.EMAIL],
    }
    defaults.update(overrides)
    return Notification(**defaults)


class TestServiceHook:
    def _service(self) -> AdminNotificationService:
        service = AdminNotificationService(mailer=None)
        service.email_sender.send_email = AsyncMock(return_value=None)  # type: ignore[method-assign]
        return service

    @pytest.mark.asyncio
    async def test_success_recorded(self) -> None:
        service = self._service()
        log = SimpleNamespace(record=AsyncMock())
        service.attach_delivery_log(log)

        result = await service.send(_notification())

        assert result.is_ok()
        log.record.assert_awaited_once()
        kwargs = log.record.await_args.kwargs
        assert kwargs["notification_type"] == NotificationType.SYSTEM_ALERT.value
        assert kwargs["recipient"] == "a@example.com"
        assert kwargs["subject"] == "Test subject"
        assert kwargs["success"] is True
        assert kwargs["error"] is None

    @pytest.mark.asyncio
    async def test_failure_recorded_with_error(self) -> None:
        service = self._service()
        service.email_sender.send_email = AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("SMTP down")
        )
        log = SimpleNamespace(record=AsyncMock())
        service.attach_delivery_log(log)

        result = await service.send(_notification())

        assert result.is_err()
        kwargs = log.record.await_args.kwargs
        assert kwargs["success"] is False
        assert "SMTP down" in kwargs["error"]

    @pytest.mark.asyncio
    async def test_broken_log_never_breaks_send(self) -> None:
        service = self._service()
        log = SimpleNamespace(record=AsyncMock(side_effect=OSError("db gone")))
        service.attach_delivery_log(log)

        result = await service.send(_notification())

        assert result.is_ok()
        assert result.unwrap().recipients_sent == 1

    @pytest.mark.asyncio
    async def test_no_log_attached_is_noop(self) -> None:
        service = self._service()

        result = await service.send(_notification())

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_disabled_type_recorded_as_failed(self) -> None:
        service = self._service()
        service.config = SimpleNamespace(
            email_from="admin@example.com",
            email_from_name="Admin",
            enabled_types=[NotificationType.PASSWORD_RESET],
        )
        log = SimpleNamespace(record=AsyncMock())
        service.attach_delivery_log(log)

        result = await service.send(_notification())

        assert result.is_ok()
        kwargs = log.record.await_args.kwargs
        assert kwargs["success"] is False
        assert "not enabled" in kwargs["error"]
        service.email_sender.send_email.assert_not_awaited()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_preference_skipped_recipient_not_logged(self) -> None:
        service = self._service()
        log = SimpleNamespace(record=AsyncMock())
        service.attach_delivery_log(log)
        recipient = NotificationRecipient(
            email="a@example.com",
            preferences={"notify_system_alert": False},
        )

        await service.send(_notification(recipients=[recipient]))

        log.record.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_notify_test_email_logged(self) -> None:
        """The diagnostics path bypasses send() but must still log (doc 42)."""
        service = AdminNotificationService(mailer=object())  # bound
        service.email_sender.send_email = AsyncMock(return_value=None)  # type: ignore[method-assign]
        log = SimpleNamespace(record=AsyncMock())
        service.attach_delivery_log(log)

        result = await service.notify_test_email(
            NotificationRecipient(email="op@example.com")
        )

        assert result.is_ok()
        kwargs = log.record.await_args.kwargs
        assert kwargs["notification_type"] == "test_email"
        assert kwargs["recipient"] == "op@example.com"
        assert kwargs["success"] is True

    @pytest.mark.asyncio
    async def test_notify_test_email_failure_logged(self) -> None:
        service = AdminNotificationService(mailer=object())
        service.email_sender.send_email = AsyncMock(  # type: ignore[method-assign]
            side_effect=ConnectionError("refused")
        )
        log = SimpleNamespace(record=AsyncMock())
        service.attach_delivery_log(log)

        result = await service.notify_test_email(
            NotificationRecipient(email="op@example.com")
        )

        assert result.is_err()
        kwargs = log.record.await_args.kwargs
        assert kwargs["success"] is False
        assert "refused" in kwargs["error"]
