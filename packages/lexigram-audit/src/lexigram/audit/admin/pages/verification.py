from __future__ import annotations

from typing import Any

from lexigram.contracts.admin import PageContent
from lexigram.contracts.admin.widget_content import EmptyContent, Stat, StatContent
from lexigram.contracts.audit import AuditMismatchReason, AuditVerifierProtocol
from lexigram.logging import get_logger

logger = get_logger(__name__)


class AuditVerificationPage:
    """Management page for /admin/audit/verification."""

    def __init__(self, verifier: AuditVerifierProtocol | None = None) -> None:
        self._verifier = verifier

    async def handle(self, request: Any) -> PageContent:
        if self._verifier is None:
            return PageContent(
                title="Audit Verification",
                body=EmptyContent(
                    title="Audit Verification Unavailable",
                    message="The audit verifier could not be resolved.",
                    icon="shield",
                ),
            )
        try:
            mismatches = await self._verifier.verify_recent()
        except Exception:
            logger.warning("audit_verification.verify_failed")
            mismatches = []

        tampered = [
            m for m in mismatches if m.reason == AuditMismatchReason.CHECKSUM_MISMATCH
        ]

        if not mismatches:
            status, status_icon = "Verified", "shield-check"
        elif tampered:
            status, status_icon = "Compromised", "shield-x"
        else:
            status, status_icon = "Unverifiable", "shield-alert"

        return PageContent(
            title="Audit Verification",
            body=StatContent(
                stats=(
                    Stat(label="Integrity Status", value=status, icon=status_icon),
                    Stat(
                        label="Mismatches Found",
                        value=str(len(mismatches)),
                        icon="alert-triangle",
                    ),
                )
            ),
        )
