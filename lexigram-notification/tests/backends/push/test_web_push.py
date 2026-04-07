"""Tests for WebPushChannel."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pywebpush import WebPushException

from lexigram.contracts.mailer import MessageDeliveryReceipt
from lexigram.contracts.notification.types import PushMessage
from lexigram.notification.backends.push.web_push import WebPushChannel
from lexigram.notification.exceptions import WebPushNotificationError
from lexigram.result import Err, Ok


@pytest.fixture
def channel() -> WebPushChannel:
    return WebPushChannel(
        vapid_private_key="""-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgUQFbX7PBKX3qTqeM
Y1TZoG0B1wI0Jq6s5JjF2VcCcqShRANCAARx7yBqMj/Nx1THwS88lPA+KB5KXQ01
qUKbHvcCs/DjYFWf8WZ3wnQj3AZyQga18dOS3N6rd5e85FWrj1e9Lg1Z
-----END PRIVATE KEY-----""",
        vapid_public_key="xHvIGozP83HVMeBLzyU8D4oHkpdDTWpQpse9wKz8ONgVZ/xZnfCdCPcBnJCBrXx05Lc3qt3l7zkVWuPV70uDVk=",
        vapid_claims_subject="mailto:test@example.com",
    )


class TestWebPushChannel:
    @pytest.mark.asyncio
    async def test_send_requires_to(self, channel: WebPushChannel) -> None:
        """send() raises ValueError if to is empty."""
        msg = PushMessage(to=[], title="Test", body="Hello")
        with pytest.raises(ValueError, match="at least one endpoint"):
            await channel.send(msg)

    @pytest.mark.asyncio
    async def test_send_returns_ok_on_success(self, channel: WebPushChannel) -> None:
        """send() returns Ok(MessageDeliveryReceipt) on success."""
        msg = PushMessage(
            to=["https://push.example.com/abc"],
            title="Test",
            body="Hello",
            data={"keys": {"p256dh": "x", "auth": "y"}},
        )

        with patch(
            "lexigram.notification.backends.push.web_push.webpush",
            return_value=MagicMock(status_code=201),
        ) as mock:
            result = await channel.send(msg)
            assert isinstance(result, Ok)
            assert isinstance(result.unwrap(), MessageDeliveryReceipt)
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_returns_err_on_410(self, channel: WebPushChannel) -> None:
        """send() returns Err(WebPushNotificationError) on 410 Gone."""
        msg = PushMessage(
            to=["https://push.example.com/abc"],
            title="Test",
            body="Hello",
        )

        exc = WebPushException("410 Gone")
        exc.status_code = 410  # type: ignore[attr-defined]
        exc.response_body = "gone"  # type: ignore[attr-defined]
        with patch(
            "lexigram.notification.backends.push.web_push.webpush",
            side_effect=exc,
        ) as mock:
            result = await channel.send(msg)
            assert isinstance(result, Err)
            err = result.unwrap_err()
            assert isinstance(err, WebPushNotificationError)
            assert err.status_code == 410
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_returns_err_on_404(self, channel: WebPushChannel) -> None:
        """send() returns Err(WebPushNotificationError) on 404 Not Found."""
        msg = PushMessage(
            to=["https://push.example.com/abc"],
            title="Test",
            body="Hello",
        )

        exc = WebPushException("404 Not Found")
        exc.status_code = 404  # type: ignore[attr-defined]
        exc.response_body = "not_found"  # type: ignore[attr-defined]
        with patch(
            "lexigram.notification.backends.push.web_push.webpush",
            side_effect=exc,
        ) as mock:
            result = await channel.send(msg)
            assert isinstance(result, Err)
            err = result.unwrap_err()
            assert err.status_code == 404
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_returns_result(self, channel: WebPushChannel) -> None:
        """health_check() returns HealthCheckResult."""
        from lexigram.contracts.core import HealthCheckResult, HealthStatus

        result = await channel.health_check()
        assert isinstance(result, HealthCheckResult)
        assert result.status in (HealthStatus.HEALTHY, HealthStatus.UNHEALTHY)

    @pytest.mark.asyncio
    async def test_send_batch_preserves_order(self, channel: WebPushChannel) -> None:
        """send_batch returns results in same order as messages."""
        messages = [
            PushMessage(to=[f"https://push.example.com/{i}"], title="T", body="B")
            for i in range(3)
        ]
        with patch(
            "lexigram.notification.backends.push.web_push.webpush",
            return_value=MagicMock(status_code=201),
        ):
            results = await channel.send_batch(messages)
            assert len(results) == 3
            for r in results:
                assert isinstance(r, Ok)
