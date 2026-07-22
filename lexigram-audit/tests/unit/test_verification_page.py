"""Focused tests for the audit verification admin page."""

from __future__ import annotations

import asyncio

from lexigram.audit.admin.pages.verification import AuditVerificationPage
from lexigram.contracts.audit import AuditMismatch, AuditMismatchReason


class _FakeRequest:
    pass


class _FakeVerifier:
    def __init__(self, mismatches: list[AuditMismatch] | Exception) -> None:
        self._mismatches = mismatches

    async def verify_recent(self) -> list[AuditMismatch]:
        if isinstance(self._mismatches, Exception):
            raise self._mismatches
        return self._mismatches


def _mismatch(reason: AuditMismatchReason, expected: str = "aa" * 32) -> AuditMismatch:
    return AuditMismatch(
        entry_id="user.login#2026-01-02T03:04:05",
        expected_checksum=expected,
        actual_checksum="bb" * 32,
        reason=reason,
    )


def _render(verifier: _FakeVerifier | None) -> str:
    page = AuditVerificationPage(verifier=verifier)
    response = asyncio.run(page.handle(_FakeRequest()))
    return response.body.decode()


class TestAuditVerificationPage:
    def test_no_verifier_unavailable(self) -> None:
        html = _render(None)
        assert "Audit Verification Unavailable" in html

    def test_verifier_failure_treats_as_clean(self) -> None:
        html = _render(_FakeVerifier(RuntimeError("boom")))
        assert "Verified" in html

    def test_clean_status(self) -> None:
        html = _render(_FakeVerifier([]))
        assert "Verified" in html
        assert "Compromised" not in html
        assert "Unverifiable" not in html
        assert "No mismatches found." in html

    def test_compromised_status(self) -> None:
        html = _render(_FakeVerifier([_mismatch(AuditMismatchReason.CHECKSUM_MISMATCH)]))
        assert "Compromised" in html
        assert "Verified" not in html

    def test_unverifiable_status_for_legacy_entries(self) -> None:
        html = _render(_FakeVerifier([_mismatch(AuditMismatchReason.NO_CHECKSUM_PRESENT)]))
        assert "Unverifiable" in html
        assert "Compromised" not in html
        assert "Verified" not in html

    def test_tampered_rows_render_only_checksum_mismatches(self) -> None:
        tampered = _mismatch(AuditMismatchReason.CHECKSUM_MISMATCH, expected="ab" * 32)
        legacy = _mismatch(AuditMismatchReason.NO_CHECKSUM_PRESENT, expected="")
        html = _render(_FakeVerifier([legacy, tampered]))
        assert "Compromised" in html
        assert "abababab" in html
        assert html.count("<tr>") == 2  # thead + the single tampered row

    def test_legacy_only_shows_no_tampered_rows(self) -> None:
        html = _render(_FakeVerifier([_mismatch(AuditMismatchReason.NO_CHECKSUM_PRESENT)]))
        assert "No mismatches found." in html
        assert "<tr>" not in html