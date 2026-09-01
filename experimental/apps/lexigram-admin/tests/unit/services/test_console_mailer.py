"""Console mailer fallback tests (R11 — docs/09-01-2026/07-mailer-onboarding.md)."""

from __future__ import annotations

import pytest

from lexigram.admin.services.notifications.console_mailer import AdminConsoleMailer
from lexigram.contracts.core import HealthStatus
from lexigram.contracts.mailer import EmailMessage
from lexigram.contracts.mailer.protocols import MailerProtocol


def _message() -> EmailMessage:
    return EmailMessage(
        to=["ops@example.com"],
        subject="Verify your email",
        body="Click: https://example.com/verify?token=abc",
    )


class TestConsoleMailer:
    def test_satisfies_mailer_protocol(self) -> None:
        assert isinstance(AdminConsoleMailer(), MailerProtocol)

    def test_marked_as_debug_fallback(self) -> None:
        assert AdminConsoleMailer.is_debug_fallback is True

    @pytest.mark.asyncio
    async def test_send_always_accepts_with_receipt(self) -> None:
        result = await AdminConsoleMailer().send(_message())
        assert result.is_ok()
        receipt = result.unwrap()
        assert receipt.backend == "admin-console"
        assert receipt.channel == "email"
        assert receipt.message_id

    @pytest.mark.asyncio
    async def test_receipts_have_unique_ids(self) -> None:
        mailer = AdminConsoleMailer()
        first = (await mailer.send(_message())).unwrap()
        second = (await mailer.send(_message())).unwrap()
        assert first.message_id != second.message_id

    @pytest.mark.asyncio
    async def test_health_check_always_healthy(self) -> None:
        health = await AdminConsoleMailer().health_check()
        assert health.status is HealthStatus.HEALTHY
