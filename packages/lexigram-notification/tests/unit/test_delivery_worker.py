"""Tests for the deferred-mail retry worker."""

from __future__ import annotations

import pytest
from lexigram.contracts.mailer import EmailMessage
from lexigram.result import Err, Ok

from lexigram.notification.delivery.stores import MemoryDeliveryStore
from lexigram.notification.delivery.worker import flush_retries


class FlakyBackend:
    """Mail backend failing the first *fail_times* sends."""

    def __init__(self, fail_times: int = 0) -> None:
        self.fail_times = fail_times
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage):
        if self.fail_times > 0:
            self.fail_times -= 1
            self.sent.append(message)
            return Err(RuntimeError("smtp unavailable"))
        self.sent.append(message)
        return Ok("receipt")


@pytest.mark.asyncio
async def test_flush_delivers_after_transient_failure() -> None:
    """A transient SMTP failure is retried successfully on the next flush."""
    store = MemoryDeliveryStore()
    backend = FlakyBackend(fail_times=1)

    from lexigram.notification.delivery.retry import RetryingMailer

    mailer = RetryingMailer(backend, store)
    message = EmailMessage(
        to=["ada@example.com"], subject="Reset", body="Click here"
    )
    await mailer.send(message)  # fails → state persisted as retrying

    # Simulate the backoff window elapsing, then flush.
    for entry in store._state.values():
        entry["retry_after"] = None
    delivered = await flush_retries(store, backend)

    assert delivered == 1
    assert len(backend.sent) == 2  # initial attempt + retry


@pytest.mark.asyncio
async def test_flush_is_noop_when_nothing_due() -> None:
    store = MemoryDeliveryStore()
    backend = FlakyBackend()

    delivered = await flush_retries(store, backend)

    assert delivered == 0
    assert backend.sent == []
