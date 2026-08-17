"""Tests for the GDPR compliance tools."""

from __future__ import annotations

from lexigram import serialization as json
import pytest

from lexigram.admin.gdpr import (
    AnonymizationRule,
    AnonymizationStrategy,
    GDPRService,
    SARStatus,
    anonymize_record,
    export_sar_json,
)


# ---------------------------------------------------------------------------
# anonymize_record
# ---------------------------------------------------------------------------

class TestAnonymizeRecord:
    def test_hash_strategy(self) -> None:
        rule = AnonymizationRule("user", fields={"email": AnonymizationStrategy.HASH})
        record = {"id": "u1", "email": "alice@example.com"}
        result = anonymize_record(record, rule)
        assert result["email"] != "alice@example.com"
        assert len(result["email"]) == 64  # SHA-256 hex

    def test_clear_strategy(self) -> None:
        rule = AnonymizationRule("user", fields={"name": AnonymizationStrategy.CLEAR})
        result = anonymize_record({"id": "u1", "name": "Alice"}, rule)
        assert result["name"] == ""

    def test_redact_strategy(self) -> None:
        rule = AnonymizationRule("user", fields={"phone": AnonymizationStrategy.REDACT})
        result = anonymize_record({"id": "u1", "phone": "+1234"}, rule)
        assert result["phone"] == "[REDACTED]"

    def test_zero_strategy(self) -> None:
        rule = AnonymizationRule("user", fields={"age": AnonymizationStrategy.ZERO})
        result = anonymize_record({"id": "u1", "age": 42}, rule)
        assert result["age"] == 0

    def test_nullify_strategy(self) -> None:
        rule = AnonymizationRule("user", fields={"notes": AnonymizationStrategy.NULLIFY})
        result = anonymize_record({"id": "u1", "notes": "sensitive"}, rule)
        assert result["notes"] is None

    def test_fake_email_strategy(self) -> None:
        rule = AnonymizationRule("user", fields={"email": AnonymizationStrategy.FAKE_EMAIL})
        result = anonymize_record({"id": "u1", "email": "real@example.com"}, rule)
        assert result["email"] == "anonymized@example.com"

    def test_preserve_id(self) -> None:
        rule = AnonymizationRule("user", fields={"id": AnonymizationStrategy.HASH}, preserve_id=True)
        record = {"id": "u1", "name": "Alice"}
        result = anonymize_record(record, rule)
        assert result["id"] == "u1"  # preserved

    def test_id_not_preserved_when_disabled(self) -> None:
        rule = AnonymizationRule("user", fields={"id": AnonymizationStrategy.HASH}, preserve_id=False)
        record = {"id": "u1"}
        result = anonymize_record(record, rule)
        assert result["id"] != "u1"

    def test_unlisted_fields_pass_through(self) -> None:
        rule = AnonymizationRule("user", fields={"email": AnonymizationStrategy.HASH})
        record = {"id": "u1", "email": "a@b.com", "role": "admin"}
        result = anonymize_record(record, rule)
        assert result["role"] == "admin"

    def test_string_strategy_shorthand(self) -> None:
        rule = AnonymizationRule("user", fields={"email": "hash"})
        result = anonymize_record({"id": "u1", "email": "a@b.com"}, rule)
        assert len(result["email"]) == 64

    def test_returns_copy_not_mutate_original(self) -> None:
        rule = AnonymizationRule("user", fields={"email": AnonymizationStrategy.CLEAR})
        original = {"id": "u1", "email": "a@b.com"}
        anonymize_record(original, rule)
        assert original["email"] == "a@b.com"


# ---------------------------------------------------------------------------
# GDPRService — anonymize
# ---------------------------------------------------------------------------

class TestGDPRServiceAnonymize:
    def test_anonymize_with_rule(self) -> None:
        svc = GDPRService()
        svc.add_rule(AnonymizationRule("user", fields={"email": "hash", "name": "clear"}))

        result = svc.anonymize("user", {"id": "u1", "email": "a@b.com", "name": "Alice"})
        assert result["name"] == ""
        assert result["email"] != "a@b.com"

    def test_anonymize_without_rule_returns_unchanged(self) -> None:
        svc = GDPRService()
        record = {"id": "u1", "email": "a@b.com"}
        result = svc.anonymize("unknown_type", record)
        assert result == record

    def test_erasure_plan_same_as_anonymize(self) -> None:
        svc = GDPRService()
        svc.add_rule(AnonymizationRule("user", fields={"email": "redact"}))
        record = {"id": "u1", "email": "a@b.com"}
        assert svc.erasure_plan("user", record) == svc.anonymize("user", record)


# ---------------------------------------------------------------------------
# GDPRService — SAR
# ---------------------------------------------------------------------------

class TestGDPRServiceSAR:
    def test_submit_sar_creates_pending(self) -> None:
        svc = GDPRService()
        sar = svc.submit_sar("u1", "alice@example.com")
        assert sar.status == SARStatus.PENDING
        assert sar.subject_id == "u1"
        assert sar.sar_id.startswith("sar-")

    def test_complete_sar(self) -> None:
        svc = GDPRService()
        sar = svc.submit_sar("u1", "a@b.com")
        completed = svc.complete_sar(sar.sar_id, {"records": [{"id": "u1"}]})
        assert completed is not None
        assert completed.status == SARStatus.COMPLETED
        assert completed.completed_at is not None
        assert completed.data_snapshot["records"]

    def test_reject_sar(self) -> None:
        svc = GDPRService()
        sar = svc.submit_sar("u1", "a@b.com")
        rejected = svc.reject_sar(sar.sar_id, "Cannot verify identity")
        assert rejected is not None
        assert rejected.status == SARStatus.REJECTED
        assert "Cannot verify identity" in rejected.notes

    def test_get_sar_returns_none_for_missing(self) -> None:
        svc = GDPRService()
        assert svc.get_sar("ghost") is None

    def test_list_sars_all(self) -> None:
        svc = GDPRService()
        svc.submit_sar("u1", "a@b.com")
        svc.submit_sar("u2", "b@b.com")
        assert len(svc.list_sars()) == 2

    def test_list_sars_filter_by_status(self) -> None:
        svc = GDPRService()
        sar1 = svc.submit_sar("u1", "a@b.com")
        svc.submit_sar("u2", "b@b.com")
        svc.complete_sar(sar1.sar_id, {})
        pending = svc.list_sars(status=SARStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].subject_id == "u2"


# ---------------------------------------------------------------------------
# GDPRService — Consent
# ---------------------------------------------------------------------------

class TestGDPRServiceConsent:
    def test_grant_consent(self) -> None:
        svc = GDPRService()
        svc.record_consent("u1", "marketing_email", granted=True)
        assert svc.has_consent("u1", "marketing_email") is True

    def test_withdraw_consent(self) -> None:
        svc = GDPRService()
        svc.record_consent("u1", "marketing_email", granted=True)
        svc.record_consent("u1", "marketing_email", granted=False)
        assert svc.has_consent("u1", "marketing_email") is False

    def test_no_consent_default_false(self) -> None:
        svc = GDPRService()
        assert svc.has_consent("u1", "marketing_email") is False

    def test_consent_history_ordered(self) -> None:
        svc = GDPRService()
        svc.record_consent("u1", "marketing_email", granted=True)
        svc.record_consent("u1", "marketing_email", granted=False)
        history = svc.consent_history("u1")
        assert len(history) == 2
        assert history[0].granted is True
        assert history[1].granted is False

    def test_different_purposes_independent(self) -> None:
        svc = GDPRService()
        svc.record_consent("u1", "marketing_email", granted=True)
        svc.record_consent("u1", "analytics", granted=False)
        assert svc.has_consent("u1", "marketing_email") is True
        assert svc.has_consent("u1", "analytics") is False


# ---------------------------------------------------------------------------
# SAR JSON export
# ---------------------------------------------------------------------------

class TestExportSarJson:
    def test_export_valid_json(self) -> None:
        svc = GDPRService()
        sar = svc.submit_sar("u1", "a@b.com")
        svc.complete_sar(sar.sar_id, {"email": "a@b.com"})
        refreshed = svc.get_sar(sar.sar_id)
        assert refreshed is not None

        output = export_sar_json(refreshed)
        parsed = json.loads(output)
        assert parsed["sar_id"] == sar.sar_id
        assert parsed["subject_id"] == "u1"
        assert parsed["status"] == "completed"
        assert "data" in parsed
