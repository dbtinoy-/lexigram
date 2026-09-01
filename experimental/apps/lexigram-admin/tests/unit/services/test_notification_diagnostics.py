"""AdminNotificationService diagnostics tests (R11, doc 07)."""

from __future__ import annotations

import pytest

from lexigram.admin.services.notifications import AdminNotificationService
from lexigram.admin.services.notifications.console_mailer import AdminConsoleMailer
from lexigram.admin.services.notifications.models import NotificationRecipient


def _recipient() -> NotificationRecipient:
    return NotificationRecipient(email="ops@example.com", name="Ops")


class TestMailerIntrospection:
    def test_unbound_state(self) -> None:
        service = AdminNotificationService(mailer=None)
        assert service.mailer_bound is False
        assert service.mailer_backend_name is None
        assert service.mailer_is_debug_fallback is False

    def test_bound_backend_name(self) -> None:
        service = AdminNotificationService(mailer=AdminConsoleMailer())
        assert service.mailer_bound is True
        assert service.mailer_backend_name == "AdminConsoleMailer"
        assert service.mailer_is_debug_fallback is True


class TestNotifyTestEmail:
    @pytest.mark.asyncio
    async def test_ok_through_console_mailer(self) -> None:
        service = AdminNotificationService(mailer=AdminConsoleMailer())
        result = await service.notify_test_email(_recipient())
        assert result.is_ok()
        assert result.unwrap().recipients_sent == 1

    @pytest.mark.asyncio
    async def test_err_when_no_mailer(self) -> None:
        service = AdminNotificationService(mailer=None)
        result = await service.notify_test_email(_recipient())
        assert result.is_err()
        assert "No mailer backend" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_backend_failure_becomes_err(self) -> None:
        class _FailingMailer:
            async def send(self, message):  # noqa: ANN001, ANN202
                raise RuntimeError("SMTP down")

            async def health_check(self, timeout: float = 5.0):  # noqa: ANN202
                raise NotImplementedError

        service = AdminNotificationService(mailer=_FailingMailer())
        result = await service.notify_test_email(_recipient())
        assert result.is_err()
        assert "SMTP down" in str(result.unwrap_err())
