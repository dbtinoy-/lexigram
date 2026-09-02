"""CSP tab rendering for the Security Center (docs/09-01-2026/31).

The Security Center controller (``controllers/security.py``, R12) owns the
``/security`` page family; these helpers render the CSP tab's content —
policy-status cards and the deduped violation table fed by the R34 report
store. They return plain HTML strings so the controller can compose them
with its shared tab chrome; no shell, guard, or routing lives here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.middleware.security_headers import resolve_report_only_csp
from lexigram.admin.settings.panel.models import DEFAULT_CSP, STRICT_CSP
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.services.security.csp_reports import CspReportStore

logger = get_logger(__name__)

#: Text shown while the violations region has no data yet.
EMPTY_STATE = "No violations reported. The candidate policy is clean so far."

#: Text shown when report ingestion never got wired at mount time.
STORE_UNAVAILABLE = (
    "CSP violation reporting is not wired on this deployment, so no "
    "reports are collected."
)


async def resolve_csp_policies(
    settings_store: Any,
) -> tuple[str, str | None, str]:
    """Return (enforced policy, report-only policy or None, ro status).

    Reads the same settings keys the security-headers middleware uses,
    best-effort: with no store (or on read failure) the compile-time
    defaults are reported, which is exactly what the middleware falls
    back to as well.
    """

    async def read(key: str) -> Any:
        if settings_store is None:
            return None
        try:
            return await settings_store.get(key)
        except Exception:  # noqa: BLE001 — cards fall back to defaults
            logger.warning("admin.security_csp.settings_read_failed", key=key)
            return None

    csp_setting = await read("admin.security.csp")
    enforced = str(csp_setting) if csp_setting else DEFAULT_CSP

    report_only = resolve_report_only_csp(
        await read("admin.security.csp_report_only")
    )
    if report_only is None:
        status = "Off"
    elif report_only == STRICT_CSP:
        status = "On — strict default"
    else:
        status = "On — custom policy"
    return enforced, report_only, status


def _badge(text: str, tone: str) -> Any:
    """Small status badge; tones map to existing token classes only."""
    from lexigram.ui import el

    tone_class = {
        "ok": "text-success border-success",
        "warn": "text-warning border-warning",
        "muted": "text-muted-foreground border-border",
    }.get(tone, "text-muted-foreground border-border")
    return el(
        "span",
        text,
        class_=f"rounded border px-2 py-0.5 text-xs font-medium {tone_class}",
    )


def _policy_pre(policy: str) -> Any:
    from lexigram.ui import el

    return el(
        "pre",
        policy,
        class_="text-xs text-muted-foreground bg-muted rounded p-3 break-all",
        style="white-space: pre-wrap;",
    )


def _card(title_row: Any, *body: Any) -> Any:
    from lexigram.ui import el

    return el(
        "div",
        el("div", title_row, class_="mb-3"),
        *body,
        class_="rounded-lg border border-border bg-card p-4",
    )


def _enforced_card(enforced: str) -> Any:
    from lexigram.ui import el

    badges = []
    if "'unsafe-inline'" in enforced:
        badges.append(_badge("contains 'unsafe-inline'", "warn"))
    if "'unsafe-eval'" in enforced:
        badges.append(_badge("contains 'unsafe-eval'", "warn"))
    if not badges:
        badges.append(_badge("strict", "ok"))
    return _card(
        el(
            "div",
            el(
                "h2",
                "Enforced policy",
                class_="text-sm font-semibold text-foreground",
            ),
            *badges,
            class_="flex flex-wrap items-center gap-2",
        ),
        _policy_pre(enforced),
        el(
            "p",
            "Sent as Content-Security-Policy on every admin response.",
            class_="text-xs text-muted-foreground mt-2",
        ),
    )


def _report_only_card(
    report_only: str | None, ro_status: str, report_endpoint: str
) -> Any:
    from lexigram.ui import el

    tone = "muted" if report_only is None else "ok"
    body: list[Any] = []
    if report_only is not None:
        body.append(_policy_pre(report_only))
        body.append(
            el(
                "p",
                f"Violations are posted to {report_endpoint} and collected "
                "below.",
                class_="text-xs text-muted-foreground mt-2",
            )
        )
    else:
        body.append(
            el(
                "p",
                "Report-only monitoring is disabled "
                "(admin.security.csp_report_only).",
                class_="text-sm text-muted-foreground",
            )
        )
    return _card(
        el(
            "div",
            el(
                "h2",
                "Report-only candidate",
                class_="text-sm font-semibold text-foreground",
            ),
            _badge(ro_status, tone),
            class_="flex flex-wrap items-center gap-2",
        ),
        *body,
    )


def render_csp_cards(
    enforced: str,
    report_only: str | None,
    ro_status: str,
    report_endpoint: str,
) -> str:
    """Render the two policy-status cards as an HTML string."""
    from lexigram.ui import el, render_to_string

    return render_to_string(
        el(
            "div",
            _enforced_card(enforced),
            _report_only_card(report_only, ro_status, report_endpoint),
            class_="grid gap-4 md:grid-cols-2",
        )
    )


def render_csp_violations_region(
    store: CspReportStore | None, fragment_url: str
) -> str:
    """Render the self-refreshing violations region as an HTML string.

    Violations arrive at unpredictable times, so the region polls
    unconditionally (one small fragment every 10s on a
    superadmin-only page). With no store attached (reporting never
    wired) a static note renders instead — no polling attributes, so
    the page does not hammer a fragment that can never change.
    """
    from lexigram.ui import el, render_to_string

    if store is None:
        return render_to_string(
            el(
                "div",
                el("p", STORE_UNAVAILABLE, class_="text-muted-foreground text-sm"),
                id="security-csp-violations",
                data_testid="security-csp-violations-region",
            )
        )

    violations = store.list_violations()
    return render_to_string(
        el(
            "div",
            el(
                "div",
                el(
                    "h2",
                    "Reported violations",
                    class_="text-lg font-semibold text-foreground",
                ),
                el(
                    "span",
                    f"{store.total_received} received · "
                    f"{len(violations)} distinct",
                    class_="text-xs text-muted-foreground",
                ),
                class_="flex items-baseline justify-between",
            ),
            _violations_table(violations),
            id="security-csp-violations",
            data_testid="security-csp-violations-region",
            hx_get=fragment_url,
            hx_trigger="every 10s",
            hx_swap="outerHTML",
            class_="space-y-3",
        )
    )


def _violations_table(violations: list[Any]) -> Any:
    from lexigram.ui import el

    if not violations:
        return el(
            "p",
            EMPTY_STATE,
            class_="text-muted-foreground text-sm",
            data_testid="security-csp-violations-empty",
        )

    def th(label: str) -> Any:
        return el(
            "th",
            label,
            class_=(
                "text-left text-xs font-medium "
                "text-muted-foreground uppercase px-3 py-2"
            ),
        )

    header = el(
        "tr",
        th("Directive"),
        th("Blocked"),
        th("Source"),
        th("Count"),
        th("First seen"),
        th("Last seen"),
        class_="border-b border-border",
    )
    rows = [_violation_row(v) for v in violations]
    return el(
        "div",
        el(
            "table",
            el("thead", header),
            el("tbody", *rows),
            class_="w-full border-collapse",
        ),
        class_="overflow-x-auto rounded-lg border border-border",
    )


def _violation_row(violation: Any) -> Any:
    from lexigram.ui import el

    def td(*children: Any, class_: str = "") -> Any:
        return el(
            "td",
            *children,
            class_=f"px-3 py-2 text-sm align-top {class_}".strip(),
        )

    source = violation.source_file or violation.document_uri or "—"
    if violation.line:
        source = f"{source}:{violation.line}"
    return el(
        "tr",
        td(
            el("code", violation.directive, class_="text-xs"),
            class_="text-foreground",
        ),
        td(violation.blocked_uri or "—", class_="text-muted-foreground break-all"),
        td(source, class_="text-muted-foreground break-all"),
        td(str(violation.count), class_="text-foreground font-medium"),
        td(violation.first_seen, class_="text-muted-foreground text-xs"),
        td(violation.last_seen, class_="text-muted-foreground text-xs"),
        class_="border-b border-border last:border-b-0",
    )


__all__ = [
    "EMPTY_STATE",
    "STORE_UNAVAILABLE",
    "render_csp_cards",
    "render_csp_violations_region",
    "resolve_csp_policies",
]
