"""Focused tests for the audit verification admin page."""

from __future__ import annotations

import asyncio

from lexigram.audit.admin.pages.verification import AuditVerificationPage
from lexigram.contracts.admin import PageContent
from lexigram.contracts.admin.widget_content import (
    EmptyContent,
    Stat,
    StatContent,
)
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


def _render(verifier: _FakeVerifier | None) -> PageContent:
    page = AuditVerificationPage(verifier=verifier)
    return asyncio.run(page.handle(_FakeRequest()))


def _stats(content: PageContent) -> dict[str, Stat]:
    assert isinstance(content.body, StatContent)
    return {s.label: s for s in content.body.stats}


class TestAuditVerificationPage:
    def test_no_verifier_unavailable(self) -> None:
        content = _render(None)
        assert content.title == "Audit Verification"
        assert isinstance(content.body, EmptyContent)
        assert content.body.title == "Audit Verification Unavailable"
        assert content.body.message == "The audit verifier could not be resolved."
        assert content.body.icon == "shield"

    def test_verifier_failure_treats_as_clean(self) -> None:
        stats = _stats(_render(_FakeVerifier(RuntimeError("boom"))))
        assert stats["Integrity Status"].value == "Verified"

    def test_clean_status(self) -> None:
        stats = _stats(_render(_FakeVerifier([])))
        assert stats["Integrity Status"].value == "Verified"
        assert stats["Integrity Status"].icon == "shield-check"
        assert stats["Mismatches Found"].value == "0"

    def test_compromised_status(self) -> None:
        stats = _stats(
            _render(_FakeVerifier([_mismatch(AuditMismatchReason.CHECKSUM_MISMATCH)]))
        )
        assert stats["Integrity Status"].value == "Compromised"
        assert stats["Integrity Status"].icon == "shield-x"
        assert stats["Mismatches Found"].value == "1"

    def test_unverifiable_status_for_legacy_entries(self) -> None:
        stats = _stats(
            _render(_FakeVerifier([_mismatch(AuditMismatchReason.NO_CHECKSUM_PRESENT)]))
        )
        assert stats["Integrity Status"].value == "Unverifiable"
        assert stats["Integrity Status"].icon == "shield-alert"
        assert stats["Mismatches Found"].value == "1"

    def test_tampered_and_legacy_count(self) -> None:
        tampered = _mismatch(AuditMismatchReason.CHECKSUM_MISMATCH, expected="ab" * 32)
        legacy = _mismatch(AuditMismatchReason.NO_CHECKSUM_PRESENT, expected="")
        stats = _stats(_render(_FakeVerifier([legacy, tampered])))
        assert stats["Integrity Status"].value == "Compromised"
        assert stats["Mismatches Found"].value == "2"

    def test_legacy_only_is_unverifiable(self) -> None:
        stats = _stats(
            _render(_FakeVerifier([_mismatch(AuditMismatchReason.NO_CHECKSUM_PRESENT)]))
        )
        assert stats["Integrity Status"].value == "Unverifiable"
        assert "Compromised" not in stats["Integrity Status"].value
