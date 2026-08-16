"""Tests for SMTPMailer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lexigram.contracts.mailer import EmailMessage
from lexigram.notification.mailer.smtp_mailer import SMTPMailer
from lexigram.notification.exceptions import SMTPMailerError


class TestSMTPMailer:
    @pytest.fixture
    def mailer(self) -> SMTPMailer:
        return SMTPMailer(
            host="smtp.example.com",
            port=587,
            username="user@example.com",
            password="secret",
            use_tls=True,
            from_email="noreply@example.com",
        )

    @pytest.fixture
    def message(self) -> EmailMessage:
        return EmailMessage(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Hello, world!",
        )

    @pytest.mark.asyncio
    async def test_send_returns_ok_on_success(
        self, mailer: SMTPMailer, message: EmailMessage
    ) -> None:
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)
            mock_smtp.sendmail = MagicMock()
            mock_smtp_cls.return_value = mock_smtp

            result = await mailer.send(message)

        assert result.is_ok()
        receipt = result.unwrap()
        assert receipt.channel == "email"
        assert receipt.backend == "smtp"

    @pytest.mark.asyncio
    async def test_send_returns_err_on_smtp_error(
        self, mailer: SMTPMailer, message: EmailMessage
    ) -> None:
        import smtplib

        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.side_effect = smtplib.SMTPException("Connection refused")
            result = await mailer.send(message)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), SMTPMailerError)

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, mailer: SMTPMailer) -> None:
        from lexigram.contracts.core import HealthStatus

        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)
            mock_smtp_cls.return_value = mock_smtp

            result = await mailer.health_check()

        assert result.status == HealthStatus.HEALTHY
