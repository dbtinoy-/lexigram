"""Unit tests for SendEmailBatchHandler."""

from __future__ import annotations

import pytest

from lexigram_example_worker.domain.campaign import CampaignPayload
from lexigram_example_worker.tasks.send_email_batch import (
    BatchResult,
    EmailBatchPayload,
    SendEmailBatchHandler,
)


# ---------------------------------------------------------------------------
# Fakes (mock at the contract boundary — fake the Protocol, not internals)
# ---------------------------------------------------------------------------


class FakeMailer:
    """Records all send calls. Controls which recipient IDs succeed."""

    def __init__(self, fail_ids: set[str] | None = None) -> None:
        self.calls: list[dict] = []
        self._fail_ids = fail_ids or set()

    async def send(self, recipient_id: str, subject: str, body_html: str) -> bool:
        """Simulate a mail send, failing for IDs in ``fail_ids``."""
        self.calls.append(
            {"recipient_id": recipient_id, "subject": subject, "body_html": body_html}
        )
        return recipient_id not in self._fail_ids


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_payload(
    recipient_ids: list[str],
    campaign_id: str = "camp-1",
) -> EmailBatchPayload:
    return EmailBatchPayload(
        campaign_id=campaign_id,
        subject="Hello",
        body_html="<p>Hi</p>",
        recipient_ids=recipient_ids,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_returns_ok_for_valid_batch() -> None:
    """Handler returns Ok(BatchResult) when all sends succeed."""
    mailer = FakeMailer()
    handler = SendEmailBatchHandler(mailer=mailer)

    payload = _make_payload(["r1", "r2", "r3"])
    result = await handler.execute(payload)

    assert result.is_ok()
    batch_result = result.unwrap()
    assert isinstance(batch_result, BatchResult)
    assert batch_result.sent == 3
    assert batch_result.failed_ids == []
    assert batch_result.campaign_id == "camp-1"


@pytest.mark.asyncio
async def test_execute_collects_failed_recipients() -> None:
    """Soft mailer failures are tracked in BatchResult.failed_ids, not raised."""
    mailer = FakeMailer(fail_ids={"r2"})
    handler = SendEmailBatchHandler(mailer=mailer)

    payload = _make_payload(["r1", "r2", "r3"])
    result = await handler.execute(payload)

    assert result.is_ok()
    batch_result = result.unwrap()
    assert batch_result.sent == 2
    assert batch_result.failed_ids == ["r2"]


@pytest.mark.asyncio
async def test_execute_returns_err_for_empty_recipient_list() -> None:
    """Handler returns Err(DomainError) when recipient_ids is empty."""
    mailer = FakeMailer()
    handler = SendEmailBatchHandler(mailer=mailer)

    payload = _make_payload([])
    result = await handler.execute(payload)

    assert result.is_err()
    # No mail should have been attempted
    assert mailer.calls == []


@pytest.mark.asyncio
async def test_execute_err_carries_campaign_id_in_details() -> None:
    """DomainError details include the campaign_id for diagnostics."""
    mailer = FakeMailer()
    handler = SendEmailBatchHandler(mailer=mailer)

    payload = _make_payload([], campaign_id="camp-broken")
    result = await handler.execute(payload)

    assert result.is_err()
    err = result.unwrap_err()
    assert "camp-broken" in str(err.details)


@pytest.mark.asyncio
async def test_execute_calls_mailer_for_every_recipient() -> None:
    """Mailer is called exactly once per recipient."""
    mailer = FakeMailer()
    handler = SendEmailBatchHandler(mailer=mailer)

    ids = [f"user-{i}" for i in range(10)]
    payload = _make_payload(ids)
    await handler.execute(payload)

    assert len(mailer.calls) == 10
    called_ids = [c["recipient_id"] for c in mailer.calls]
    assert called_ids == ids


@pytest.mark.asyncio
async def test_from_campaign_builds_correct_batch_payload() -> None:
    """EmailBatchPayload.from_campaign correctly slices the campaign payload."""
    campaign = CampaignPayload(
        campaign_id="c1",
        subject="Test",
        body_html="<b>Hi</b>",
        recipient_ids=["a", "b", "c", "d"],
        batch_size=2,
    )
    batch = EmailBatchPayload.from_campaign(campaign, ["a", "b"])

    assert batch.campaign_id == "c1"
    assert batch.subject == "Test"
    assert batch.recipient_ids == ["a", "b"]


@pytest.mark.asyncio
async def test_all_recipients_fail_returns_ok_with_all_in_failed_ids() -> None:
    """Even if every recipient fails, Ok is returned — partial delivery is valid."""
    mailer = FakeMailer(fail_ids={"r1", "r2"})
    handler = SendEmailBatchHandler(mailer=mailer)

    payload = _make_payload(["r1", "r2"])
    result = await handler.execute(payload)

    assert result.is_ok()
    batch_result = result.unwrap()
    assert batch_result.sent == 0
    assert set(batch_result.failed_ids) == {"r1", "r2"}
