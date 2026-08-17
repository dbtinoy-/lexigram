"""GDPRService — orchestrates anonymization, SAR tracking, and consent."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lexigram.admin.gdpr.anonymizer import anonymize_record
from lexigram.admin.gdpr.models import (
    AnonymizationRule,
    ConsentRecord,
    SARStatus,
    SubjectAccessRequest,
)


class GDPRService:
    """Orchestrates GDPR compliance operations.

    Manages anonymization rules, Subject Access Requests, and consent records.
    Backed by in-process stores by default — wire a DB-backed store for
    production via subclassing or dependency injection.
    """

    def __init__(self) -> None:
        self._rules: dict[str, AnonymizationRule] = {}
        self._sars: dict[str, SubjectAccessRequest] = {}
        self._consents: dict[str, list[ConsentRecord]] = {}
        self._sar_counter = 0
        self._consent_counter = 0

    # ------------------------------------------------------------------
    # Anonymization rules
    # ------------------------------------------------------------------

    def add_rule(self, rule: AnonymizationRule) -> None:
        """Register an anonymization rule for a resource type.

        Args:
            rule: :class:`AnonymizationRule` to register.
        """
        self._rules[rule.resource_type] = rule

    def get_rule(self, resource_type: str) -> AnonymizationRule | None:
        """Return the rule for *resource_type*, or ``None``.

        Args:
            resource_type: Resource name.
        """
        return self._rules.get(resource_type)

    def anonymize(self, resource_type: str, record: dict[str, Any]) -> dict[str, Any]:
        """Anonymize *record* using the registered rule for *resource_type*.

        If no rule is registered, the record is returned unchanged (safe
        default — no data destruction without an explicit rule).

        Args:
            resource_type: Resource name.
            record: Original record dict.

        Returns:
            Anonymized copy of the record.
        """
        rule = self._rules.get(resource_type)
        if rule is None:
            return dict(record)
        return anonymize_record(record, rule)

    # ------------------------------------------------------------------
    # Right to erasure
    # ------------------------------------------------------------------

    def erasure_plan(
        self, resource_type: str, record: dict[str, Any]
    ) -> dict[str, Any]:
        """Return what the record would look like after right-to-erasure.

        Does **not** persist anything — callers must apply the returned dict
        to their data source.

        Args:
            resource_type: Resource name.
            record: Current record dict.

        Returns:
            Anonymized / erased record dict.
        """
        return self.anonymize(resource_type, record)

    # ------------------------------------------------------------------
    # Subject Access Requests
    # ------------------------------------------------------------------

    def submit_sar(
        self, subject_id: str, subject_email: str, *, notes: str = ""
    ) -> SubjectAccessRequest:
        """Create and track a new Subject Access Request.

        Args:
            subject_id: Identifier of the data subject.
            subject_email: Contact email for the response.
            notes: Optional notes.

        Returns:
            Newly created :class:`SubjectAccessRequest`.
        """
        self._sar_counter += 1
        sar = SubjectAccessRequest(
            sar_id=f"sar-{self._sar_counter:06d}",
            subject_id=subject_id,
            subject_email=subject_email,
            notes=notes,
        )
        self._sars[sar.sar_id] = sar
        return sar

    def complete_sar(
        self, sar_id: str, data_snapshot: dict[str, Any]
    ) -> SubjectAccessRequest | None:
        """Mark an SAR as completed and attach the exported data.

        Args:
            sar_id: SAR identifier.
            data_snapshot: Exported data for the subject.

        Returns:
            Updated :class:`SubjectAccessRequest` or ``None`` if not found.
        """
        sar = self._sars.get(sar_id)
        if sar is None:
            return None
        sar.status = SARStatus.COMPLETED
        sar.completed_at = datetime.now(UTC)
        sar.data_snapshot = data_snapshot
        return sar

    def reject_sar(self, sar_id: str, reason: str = "") -> SubjectAccessRequest | None:
        """Reject an SAR (e.g. identity verification failed).

        Args:
            sar_id: SAR identifier.
            reason: Reason for rejection (stored in notes).

        Returns:
            Updated :class:`SubjectAccessRequest` or ``None`` if not found.
        """
        sar = self._sars.get(sar_id)
        if sar is None:
            return None
        sar.status = SARStatus.REJECTED
        if reason:
            sar.notes = f"Rejected: {reason}"
        return sar

    def get_sar(self, sar_id: str) -> SubjectAccessRequest | None:
        """Return an SAR by ID.

        Args:
            sar_id: SAR identifier.
        """
        return self._sars.get(sar_id)

    def list_sars(
        self, *, status: SARStatus | None = None
    ) -> list[SubjectAccessRequest]:
        """Return all SARs, optionally filtered by status.

        Args:
            status: When provided, only return SARs with this status.
        """
        sars = list(self._sars.values())
        if status:
            return [s for s in sars if s.status == status]
        return sars

    # ------------------------------------------------------------------
    # Consent
    # ------------------------------------------------------------------

    def record_consent(
        self,
        subject_id: str,
        purpose: str,
        *,
        granted: bool,
        metadata: dict[str, Any] | None = None,
    ) -> ConsentRecord:
        """Record a consent grant or withdrawal.

        Args:
            subject_id: Data subject identifier.
            purpose: Consent purpose slug (e.g. ``"marketing_email"``).
            granted: ``True`` = granted, ``False`` = withdrawn.
            metadata: Optional context (IP, source, etc.).

        Returns:
            Newly created :class:`ConsentRecord`.
        """
        self._consent_counter += 1
        record = ConsentRecord(
            consent_id=f"con-{self._consent_counter:06d}",
            subject_id=subject_id,
            purpose=purpose,
            granted=granted,
            metadata=metadata or {},
        )
        self._consents.setdefault(subject_id, []).append(record)
        return record

    def has_consent(self, subject_id: str, purpose: str) -> bool:
        """Return ``True`` if the subject's most recent consent for *purpose* is granted.

        Args:
            subject_id: Data subject identifier.
            purpose: Consent purpose slug.
        """
        events = self._consents.get(subject_id, [])
        for event in reversed(events):
            if event.purpose == purpose:
                return event.granted
        return False

    def consent_history(self, subject_id: str) -> list[ConsentRecord]:
        """Return all consent events for a subject (oldest first).

        Args:
            subject_id: Data subject identifier.
        """
        return list(self._consents.get(subject_id, []))


__all__ = [
    "GDPRService",
]
