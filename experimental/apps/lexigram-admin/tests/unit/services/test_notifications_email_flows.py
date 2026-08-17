"""Unit tests for admin email verification + email OTP notifications."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.services.notifications import AdminNotificationService


class FakeMailer:
    """MailerProtocol fake that captures sent EmailMessages."""

    def __init__(self) -> None:
        self.sent: list[object] = []

    async def send(self, message: object) -> MagicMock:
        self.sent.append(message)
        result = MagicMock()
        result.is_err.return_value = False
        return result

    async def health_check(self) -> MagicMock:
        result = MagicMock()
        result.is_ok.return_value = True
        return result


def _subject(message: object) -> str:
    return getattr(message, "subject", "")


def _html(message: object) -> str:
    return getattr(message, "html_body", "") or getattr(message, "body", "")


@pytest.mark.asyncio
async def test_notify_email_verification_renders_verify_url() -> None:
    mailer = FakeMailer()
    service = AdminNotificationService(mailer=mailer)

    result = await service.notify_email_verification(
        "admin@example.com",
        "Admin User",
        "http://panel/admin/verify-email/TOKEN123",
    )

    assert result.is_ok()
    assert len(mailer.sent) == 1
    message = mailer.sent[0]
    assert _subject(message) == "Verify your email address"
    assert "TOKEN123" in _html(message)
    assert "24 hours" in _html(message)


@pytest.mark.asyncio
async def test_notify_email_otp_renders_code() -> None:
    mailer = FakeMailer()
    service = AdminNotificationService(mailer=mailer)

    result = await service.notify_email_otp(
        "admin@example.com",
        "Admin User",
        "123456",
    )

    assert result.is_ok()
    assert len(mailer.sent) == 1
    message = mailer.sent[0]
    assert _subject(message) == "Your verification code"
    assert "123456" in _html(message)
    assert "10 minutes" in _html(message)


@pytest.mark.asyncio
async def test_notify_email_verification_fails_without_mailer() -> None:
    service = AdminNotificationService(mailer=None)

    result = await service.notify_email_verification(
        "admin@example.com",
        "Admin User",
        "http://panel/admin/verify-email/TOKEN123",
    )

    assert result.is_err()
    assert "No mailer backend is configured" in str(result.unwrap_err())


@pytest.mark.asyncio
async def test_notify_email_otp_fails_without_mailer() -> None:
    service = AdminNotificationService(mailer=None)

    result = await service.notify_email_otp(
        "admin@example.com",
        "Admin User",
        "123456",
    )

    assert result.is_err()
    assert "No mailer backend is configured" in str(result.unwrap_err())


@pytest.mark.asyncio
async def test_notify_email_otp_propagates_mailer_failure() -> None:
    mailer = MagicMock()
    failure = MagicMock()
    failure.is_err.return_value = True
    failure.unwrap_err.return_value = RuntimeError("smtp down")
    mailer.send = AsyncMock(return_value=failure)
    service = AdminNotificationService(mailer=mailer)

    result = await service.notify_email_otp("admin@example.com", "Admin", "123456")

    assert result.is_err()
    assert "smtp down" in str(result.unwrap_err())
