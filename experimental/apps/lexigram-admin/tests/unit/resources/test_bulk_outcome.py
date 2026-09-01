"""BulkOutcome value-object tests (R14 — docs/09-01-2026/09-bulk-ux.md)."""

from __future__ import annotations

from lexigram.admin.resources.bulk_outcome import BulkOutcome


def _outcome(verb: str = "Deleted", total: int = 5) -> BulkOutcome:
    return BulkOutcome(verb=verb, total=total)


class TestAccounting:
    def test_counters(self) -> None:
        outcome = _outcome(total=3)
        outcome.record_success()
        outcome.record_failure("a", "not found")
        outcome.record_failure("b", "error")
        assert outcome.succeeded == 1
        assert outcome.failed == 2
        assert outcome.failures == [("a", "not found"), ("b", "error")]

    def test_all_ok(self) -> None:
        outcome = _outcome(total=2)
        outcome.record_success()
        outcome.record_success()
        assert outcome.all_ok is True
        outcome.record_failure("x", "error")
        assert outcome.all_ok is False

    def test_failure_ids_coerced_to_str(self) -> None:
        outcome = _outcome(total=1)
        outcome.record_failure(123, "not found")  # type: ignore[arg-type]
        assert outcome.failures == [("123", "not found")]


class TestMessage:
    def test_all_success_message_is_legacy_format(self) -> None:
        # The happy path must stay byte-identical to the pre-R14 messages.
        outcome = _outcome(verb="Deleted", total=3)
        for _ in range(3):
            outcome.record_success()
        assert outcome.message() == "Deleted 3 item(s)"

    def test_partial_failure_message(self) -> None:
        outcome = _outcome(verb="Deleted", total=3)
        outcome.record_success()
        outcome.record_success()
        outcome.record_failure("a1", "not found")
        assert outcome.message() == (
            "Deleted 2 of 3 item(s) - 1 failed: a1 (not found)"
        )

    def test_zero_success_message(self) -> None:
        outcome = _outcome(verb="Restored", total=2)
        outcome.record_failure("a", "not found")
        outcome.record_failure("b", "forbidden")
        assert outcome.message() == (
            "Restored 0 of 2 item(s) - 2 failed: a (not found), b (forbidden)"
        )

    def test_details_capped_with_and_n_more(self) -> None:
        outcome = _outcome(verb="Purged", total=6)
        for i in range(6):
            outcome.record_failure(f"id{i}", "not found")
        message = outcome.message()
        assert "6 failed" in message
        assert "id0 (not found), id1 (not found), id2 (not found)" in message
        assert "and 3 more" in message
        assert "id3" not in message

    def test_max_details_parameter(self) -> None:
        outcome = _outcome(total=3)
        for i in range(3):
            outcome.record_failure(f"id{i}", "error")
        message = outcome.message(max_details=1)
        assert "id0 (error) and 2 more" in message

    def test_long_ids_truncated(self) -> None:
        outcome = _outcome(total=1)
        outcome.record_failure("abcdefgh12345678", "not found")
        message = outcome.message()
        assert "abcdefgh..." in message
        assert "abcdefgh12345678" not in message

    def test_short_ids_not_truncated(self) -> None:
        outcome = _outcome(total=1)
        outcome.record_failure("abcd1234", "not found")
        assert "abcd1234 (not found)" in outcome.message()
        assert "..." not in outcome.message()

    def test_message_is_ascii_header_safe(self) -> None:
        # The message travels in the HX-Trigger response header, and HTTP
        # headers are latin-1 — non-ASCII raises UnicodeEncodeError there.
        outcome = _outcome(verb="Deleted", total=10)
        outcome.record_success()
        for i in range(9):
            outcome.record_failure(f"long-identifier-{i}", "rejected by storage")
        outcome.message().encode("latin-1")  # must not raise
        assert outcome.message().isascii()

    def test_non_ascii_record_ids_are_header_safe(self) -> None:
        outcome = _outcome(total=1)
        outcome.record_failure("café-Ω-id", "not found")
        message = outcome.message()
        message.encode("latin-1")  # must not raise
        assert message.isascii()
        # Full id is still available for the structured log.
        assert outcome.log_fields()["failures"] == [
            {"id": "café-Ω-id", "reason": "not found"}
        ]


class TestToastType:
    def test_success(self) -> None:
        outcome = _outcome(total=1)
        outcome.record_success()
        assert outcome.toast_type() == "success"

    def test_warning_on_partial(self) -> None:
        outcome = _outcome(total=2)
        outcome.record_success()
        outcome.record_failure("a", "error")
        assert outcome.toast_type() == "warning"

    def test_error_on_total_failure(self) -> None:
        outcome = _outcome(total=1)
        outcome.record_failure("a", "error")
        assert outcome.toast_type() == "error"


class TestLogFields:
    def test_full_untruncated_failures_in_log(self) -> None:
        outcome = _outcome(verb="Deleted", total=2)
        outcome.record_success()
        outcome.record_failure("abcdefgh12345678", "rejected by storage")
        fields = outcome.log_fields()
        assert fields["verb"] == "Deleted"
        assert fields["total"] == 2
        assert fields["succeeded"] == 1
        assert fields["failed"] == 1
        assert fields["failures"] == [
            {"id": "abcdefgh12345678", "reason": "rejected by storage"}
        ]
