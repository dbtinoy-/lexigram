"""GDPR data models — anonymization rules, SAR, and consent records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class AnonymizationStrategy(StrEnum):
    """Strategy for anonymizing a single field.

    * ``HASH`` — SHA-256 hex digest (irreversible, retains uniqueness)
    * ``CLEAR`` — Replace with empty string
    * ``REDACT`` — Replace with ``"[REDACTED]"``
    * ``ZERO`` — Replace with ``0`` (for numeric fields)
    * ``NULLIFY`` — Replace with ``None``
    * ``FAKE_EMAIL`` — Replace with ``"anonymized@example.com"``
    """

    HASH = "hash"
    CLEAR = "clear"
    REDACT = "redact"
    ZERO = "zero"
    NULLIFY = "nullify"
    FAKE_EMAIL = "fake_email"


@dataclass
class AnonymizationRule:
    """Per-resource-type anonymization configuration.

    Attributes:
        resource_type: Resource name this rule applies to (e.g. ``"user"``).
        fields: Mapping of field name → :class:`AnonymizationStrategy` (or
            string shorthand).
        preserve_id: When ``True``, the ``id`` field is always kept as-is.
    """

    resource_type: str
    fields: dict[str, str | AnonymizationStrategy] = field(default_factory=dict)
    preserve_id: bool = True


class SARStatus(StrEnum):
    """Subject Access Request lifecycle status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


@dataclass
class SubjectAccessRequest:
    """A GDPR Subject Access Request.

    Attributes:
        sar_id: Unique identifier.
        subject_id: User/subject identifier who made the request.
        subject_email: Contact email for the response.
        status: Current lifecycle status.
        requested_at: UTC timestamp when the request was submitted.
        completed_at: UTC timestamp when the request was fulfilled.
        data_snapshot: Exported data (set when completed).
        notes: Internal notes.
    """

    sar_id: str
    subject_id: str
    subject_email: str
    status: SARStatus = SARStatus.PENDING
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    data_snapshot: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass
class ConsentRecord:
    """A single consent event for a subject.

    Attributes:
        consent_id: Unique ID.
        subject_id: Who gave or withdrew consent.
        purpose: Consent purpose slug (e.g. ``"marketing_email"``).
        granted: ``True`` for grant, ``False`` for withdrawal.
        recorded_at: UTC timestamp of the event.
        metadata: Additional context (IP, user-agent, etc.).
    """

    consent_id: str
    subject_id: str
    purpose: str
    granted: bool
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "AnonymizationRule",
    "AnonymizationStrategy",
    "ConsentRecord",
    "SARStatus",
    "SubjectAccessRequest",
]
