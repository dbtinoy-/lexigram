"""Panel-driven sender identity + mailer health tests (R39, doc 35)."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.config import AdminNotificationConfig
from lexigram.admin.services.notifications import AdminNotificationService
from lexigram.admin.services.notifications.console_mailer import AdminConsoleMailer


class _FakeStore:
    """StoreBase-alike backed by a dict, counting reads."""

    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self.values = values or {}
        self.reads = 0
        self.fail = False

    async def get(self, key: str, default: Any = None) -> Any:
        self.reads += 1
        if self.fail:
            raise RuntimeError("store down")
        return self.values.get(key, default)


def _service(store: _FakeStore | None = None, ttl: float = 30.0):
    service = AdminNotificationService(
        mailer=AdminConsoleMailer(),
        config=AdminNotificationConfig(),
    )
    if store is not None:
        service.attach_settings_store(store, ttl=ttl)
    return service


class TestSenderIdentityOverride:
    @pytest.mark.asyncio
    async def test_no_store_keeps_config_identity(self) -> None:
        service = _service()
        email, name = await service.effective_sender()
        assert email == service.config.email_from
        assert name == service.config.email_from_name

    @pytest.mark.asyncio
    async def test_override_applied(self) -> None:
        store = _FakeStore(
            {
                "admin.notifications.email_from": "hello@lexigram.dev",
                "admin.notifications.email_from_name": "Lexigram",
            }
        )
        service = _service(store)
        assert await service.effective_sender() == ("hello@lexigram.dev", "Lexigram")
        assert service.email_sender.from_email == "hello@lexigram.dev"

    @pytest.mark.asyncio
    async def test_empty_values_reset_to_config_defaults(self) -> None:
        store = _FakeStore(
            {
                "admin.notifications.email_from": "hello@lexigram.dev",
                "admin.notifications.email_from_name": "Lexigram",
            }
        )
        service = _service(store, ttl=0.0)
        await service.effective_sender()
        store.values = {
            "admin.notifications.email_from": "",
            "admin.notifications.email_from_name": "   ",
        }
        email, name = await service.effective_sender()
        assert email == service.config.email_from
        assert name == service.config.email_from_name

    @pytest.mark.asyncio
    async def test_ttl_caches_reads(self) -> None:
        store = _FakeStore({"admin.notifications.email_from": "a@b.dev"})
        service = _service(store, ttl=60.0)
        await service.effective_sender()
        await service.effective_sender()
        assert store.reads == 2  # both keys, once

    @pytest.mark.asyncio
    async def test_ttl_zero_refreshes_every_call(self) -> None:
        store = _FakeStore()
        service = _service(store, ttl=0.0)
        await service.effective_sender()
        await service.effective_sender()
        assert store.reads == 4

    @pytest.mark.asyncio
    async def test_store_error_keeps_current_identity(self) -> None:
        store = _FakeStore({"admin.notifications.email_from": "a@b.dev"})
        service = _service(store, ttl=0.0)
        await service.effective_sender()
        store.fail = True
        email, _ = await service.effective_sender()
        assert email == "a@b.dev"  # stale-over-broken

    @pytest.mark.asyncio
    async def test_store_error_advances_retry_timestamp(self) -> None:
        store = _FakeStore()
        store.fail = True
        service = _service(store, ttl=60.0)
        await service.effective_sender()
        reads_after_first = store.reads
        await service.effective_sender()
        assert store.reads == reads_after_first  # no hammering within TTL

    @pytest.mark.asyncio
    async def test_send_path_uses_override(self) -> None:
        sent: list[Any] = []

        class _CaptureMailer:
            async def send(self, message: Any) -> Any:
                from lexigram.result import Ok

                sent.append(message)
                return Ok(type("R", (), {"message_id": "m1"})())

        service = AdminNotificationService(
            mailer=_CaptureMailer(), config=AdminNotificationConfig()
        )
        service.attach_settings_store(
            _FakeStore({"admin.notifications.email_from": "ops@lexigram.dev"})
        )
        from lexigram.admin.services.notifications.models import (
            NotificationRecipient,
        )

        result = await service.notify_test_email(
            NotificationRecipient(email="to@example.com", name="To")
        )
        assert result.is_ok()
        assert len(sent) == 1
        assert sent[0].from_email == "ops@lexigram.dev"


class TestMailerHealth:
    @pytest.mark.asyncio
    async def test_console_mailer_reports_health(self) -> None:
        service = _service()
        health = await service.mailer_health()
        assert health is not None
        assert getattr(health.status, "value", health.status) in {
            "healthy",
            "degraded",
            "unhealthy",
            "unknown",
            "starting",
        }

    @pytest.mark.asyncio
    async def test_no_mailer_returns_none(self) -> None:
        service = AdminNotificationService(mailer=None)
        assert await service.mailer_health() is None

    @pytest.mark.asyncio
    async def test_backend_without_health_check_returns_none(self) -> None:
        class _BareMailer:
            async def send(self, message: Any) -> Any:  # pragma: no cover
                raise NotImplementedError

        service = AdminNotificationService(mailer=_BareMailer())
        assert await service.mailer_health() is None

    @pytest.mark.asyncio
    async def test_raising_health_check_returns_none(self) -> None:
        class _BrokenMailer:
            async def send(self, message: Any) -> Any:  # pragma: no cover
                raise NotImplementedError

            async def health_check(self, timeout: float = 5.0) -> Any:
                raise RuntimeError("probe failed")

        service = AdminNotificationService(mailer=_BrokenMailer())
        assert await service.mailer_health() is None
