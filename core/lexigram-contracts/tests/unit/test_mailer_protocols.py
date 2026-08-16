"""Tests for mailer protocol definitions."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.contracts.mailer.protocols import MailerProtocol


class TestMailerProtocol:
    """Tests for MailerProtocol."""

    @pytest.mark.asyncio
    async def test_has_send_method(self) -> None:
        """Test protocol has send async method."""

        from lexigram.contracts.mailer.types import (
            MessageDeliveryReceipt,
            MessagePriority,
        )
        from lexigram.result import Ok

        class Mailer:
            async def send(
                self, message: Any
            ) -> Any:
                return Ok(
                    MessageDeliveryReceipt(
                        message_id="msg-123",
                        backend="smtp",
                        channel="email",
                    )
                )

        mailer = Mailer()

        class FakeMessage:
            subject = "test"
            priority = MessagePriority.NORMAL

        result = await mailer.send(FakeMessage())
        assert result.is_ok()
        assert result.unwrap().message_id == "msg-123"

    @pytest.mark.asyncio
    async def test_has_health_check_method(self) -> None:
        """Test protocol has health_check async method."""

        class Mailer:
            async def health_check(self, timeout: float = 5.0) -> Any:
                return {"status": "healthy", "latency_ms": 10.0}

        mailer = Mailer()
        result = await mailer.health_check()
        assert result["status"] == "healthy"

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        from lexigram.contracts.mailer.types import MessageDeliveryReceipt
        from lexigram.result import Ok

        class Mailer:
            async def send(self, message: Any) -> Any:
                return Ok(
                    MessageDeliveryReceipt(
                        message_id="",
                        backend="",
                        channel="",
                    )
                )

            async def health_check(self, timeout: float = 5.0) -> Any:
                return {}

        assert isinstance(Mailer(), MailerProtocol)
