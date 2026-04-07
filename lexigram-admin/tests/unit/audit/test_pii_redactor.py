"""Tests for DefaultPiiRedactor."""

from __future__ import annotations

from lexigram.admin.audit.redactor import DefaultPiiRedactor


class TestDefaultPiiRedactor:
    """DefaultPiiRedactor tests."""

    def test_redacts_email_field(self) -> None:
        r = DefaultPiiRedactor(field_denylist={"email", "phone", "password_hash"})
        out = r.redact({"id": 1, "email": "u@example.com", "name": "U"})
        assert out == {"id": 1, "email": "<redacted>", "name": "U"}

    def test_redacts_nested_fields(self) -> None:
        r = DefaultPiiRedactor(field_denylist={"ssn"})
        out = r.redact({"user": {"id": 1, "ssn": "123-45-6789"}})
        assert out == {"user": {"id": 1, "ssn": "<redacted>"}}

    def test_pattern_redaction_emails_in_string_values(self) -> None:
        r = DefaultPiiRedactor(patterns=("email",))
        out = r.redact({"note": "contact me at foo@bar.com if needed"})
        assert "foo@bar.com" not in out["note"]

    def test_pattern_redaction_phone_in_string_values(self) -> None:
        r = DefaultPiiRedactor(patterns=("phone",))
        out = r.redact({"note": "call +1-555-123-4567 for help"})
        assert "+1-555-123-4567" not in out["note"]

    def test_unknown_patterns_ignored(self) -> None:
        r = DefaultPiiRedactor(patterns=("unknown",))
        out = r.redact({"key": "value"})
        assert out == {"key": "value"}

    def test_empty_denylist_noop(self) -> None:
        r = DefaultPiiRedactor()
        out = r.redact({"email": "u@example.com"})
        assert out == {"email": "u@example.com"}

    def test_redacts_in_lists(self) -> None:
        r = DefaultPiiRedactor(field_denylist={"email"})
        out = r.redact({"users": [{"email": "a@b.com"}, {"email": "c@d.com"}]})
        assert out == {"users": [{"email": "<redacted>"}, {"email": "<redacted>"}]}
