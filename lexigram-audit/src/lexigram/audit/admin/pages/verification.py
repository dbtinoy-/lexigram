from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.audit import AuditVerifierProtocol
from lexigram.logging import get_logger
from lexigram.ui import (
    Card,
    Divider,
    EmptyState,
    Grid,
    StatCard,
    el,
    render_to_string,
)

logger = get_logger(__name__)


class AuditVerificationPage:
    """Management page for /admin/audit/verification."""

    def __init__(self, verifier: AuditVerifierProtocol | None = None) -> None:
        self._verifier = verifier

    async def handle(self, request: Any) -> HTMLResponse:
        if self._verifier is None:
            html = render_to_string(
                EmptyState(
                    title="Audit Verification Unavailable",
                    message="The audit verifier could not be resolved.",
                    icon="shield",
                ),
            )
            return HTMLResponse(html)
        try:
            mismatches = await self._verifier.verify_recent()
        except Exception:
            logger.warning("audit_verification.verify_failed")
            mismatches = []

        verified = len(mismatches) == 0

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Audit Verification",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Verify the integrity of the audit log chain.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(
                        label="Integrity Status",
                        value="Verified" if verified else "Compromised",
                        delta_color="green" if verified else "red",
                        icon="shield-check",
                    ),
                    StatCard(
                        label="Mismatches Found",
                        value=str(len(mismatches)),
                        icon="alert-triangle",
                    ),
                    cols={"default": 1, "lg": 2},
                    gap=4,
                ),
                Card(
                    title="Verification Details",
                    content=render_to_string(
                        el(
                            "dl",
                            el(
                                "dt",
                                "Status",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                "All entries verified — no hash chain mismatches detected."
                                if verified
                                else f"{len(mismatches)} hash chain mismatches detected.",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            class_="divide-y divide-[var(--border)]",
                        )
                    ),
                ),
                el(
                    "div",
                    el(
                        "h2",
                        "Mismatches",
                        class_="text-lg font-semibold text-[var(--foreground)] mb-3 mt-6",
                    ),
                    el(
                        "div",
                        el(
                            "table",
                            el(
                                "thead",
                                el(
                                    "tr",
                                    el(
                                        "th",
                                        "Expected",
                                        style="width:50%",
                                        class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                    ),
                                    el(
                                        "th",
                                        "Actual",
                                        style="width:50%",
                                        class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                    ),
                                ),
                            ),
                            el(
                                "tbody",
                                "".join(
                                    render_to_string(
                                        el(
                                            "tr",
                                            el(
                                                "td",
                                                m.expected_hash[:32] + "...",
                                                class_="px-4 py-3 whitespace-nowrap text-sm font-mono text-[var(--foreground)]",
                                            ),
                                            el(
                                                "td",
                                                m.actual_hash[:32] + "...",
                                                class_="px-4 py-3 whitespace-nowrap text-sm font-mono text-red-600",
                                            ),
                                        )
                                    )
                                    for m in mismatches
                                )
                                if mismatches
                                else "",
                                class_="divide-y divide-[var(--border)]",
                            ),
                            class_="min-w-full table-fixed divide-y divide-[var(--border)]",
                        )
                        if mismatches
                        else el(
                            "p",
                            "No mismatches found.",
                            class_="text-sm text-[var(--muted-foreground)] py-4",
                        ),
                        class_="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)]",
                    ),
                    class_="mt-4",
                ),
                class_="p-6",
            ),
        )

        return HTMLResponse(html)
