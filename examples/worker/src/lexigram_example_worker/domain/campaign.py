"""Campaign domain model and related events.

A :class:`Campaign` groups together the metadata for a bulk email send.
When a campaign is accepted for processing a :class:`CampaignQueued` domain
event is emitted so that downstream consumers can begin dispatching batches.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from lexigram.contracts.domain.events import DomainEvent


@dataclass(frozen=True)
class CampaignPayload:
    """Serialisable payload carried inside a queue ``BusMessage``.

    Attributes:
        campaign_id: Identifier of the originating campaign.
        subject: Email subject line.
        body_html: HTML body of the email.
        recipient_ids: Ordered list of recipient identifiers to contact.
        batch_size: Maximum recipients per processing batch.
    """

    campaign_id: str
    subject: str
    body_html: str
    recipient_ids: list[str]
    batch_size: int = 50


@dataclass
class Campaign:
    """Represents a bulk email campaign.

    Campaigns are immutable value objects once created — mutations produce a
    new instance via dataclass ``replace``.

    Attributes:
        id: Globally unique campaign identifier (UUID4).
        name: Human-readable campaign name.
        subject: Email subject line.
        body_html: HTML body template.
        recipient_ids: Full list of recipient identifiers.
        batch_size: Number of recipients processed per worker batch.
        created_at: UTC timestamp of campaign creation.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    subject: str = ""
    body_html: str = ""
    recipient_ids: list[str] = field(default_factory=list)
    batch_size: int = 50
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_payload(self) -> CampaignPayload:
        """Build the wire-serialisable payload for queuing.

        Returns:
            :class:`CampaignPayload` ready to embed in a ``BusMessage``.
        """
        return CampaignPayload(
            campaign_id=self.id,
            subject=self.subject,
            body_html=self.body_html,
            recipient_ids=list(self.recipient_ids),
            batch_size=self.batch_size,
        )


@dataclass(frozen=True)
class CampaignQueued(DomainEvent):
    """Emitted when a campaign is accepted and placed on the processing queue.

    Attributes:
        campaign_id: Identifier of the queued campaign.
        recipient_count: Total number of recipients to be contacted.
        batch_size: Batch size used for distribution.
    """

    campaign_id: str = ""
    recipient_count: int = 0
    batch_size: int = 50

    def to_dict(self) -> dict[str, Any]:
        """Serialise event to a plain dictionary.

        Returns:
            Dictionary representation including base event fields.
        """
        return {
            **super().to_dict(),
            "campaign_id": self.campaign_id,
            "recipient_count": self.recipient_count,
            "batch_size": self.batch_size,
        }


__all__ = ["Campaign", "CampaignPayload", "CampaignQueued"]
