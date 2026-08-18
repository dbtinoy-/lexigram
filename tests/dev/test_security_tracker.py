from __future__ import annotations

from dev.audit.generators.security_tracker import (
    parse_tracker_rows,
    parse_verified_clean,
    row_is_done,
    severity_counts,
)

SAMPLE = """\
# AUDIT_TRACKER.md

| # | Area | Severity mix | Spec | Plan |
|---|------|--------------|------|------|
| 1 | **P0 session-secret** | Critical \u00d73 | `specs/2026-08-16-security-p0-session-secret-design.md` | `plans/2026-08-16-security-p0-session-secret.md` — **EXECUTED 2026-08-16** |
| 26 | **First-run setup wizard race/takeover** | §28 | High \u00d71 | `specs/2026-08-16-security-setup-wizard-takeover-design.md` | `plans/2026-08-16-security-setup-wizard-takeover.md` — **EXECUTED 2026-08-17 (Lane 1)** |
| 50 | **Redis persistence fails open** | High \u00d71 | `specs/2026-08-18-security-ai-governance-redis-failopen-design.md` | Not yet written |

## 12a. Round 10 — Findings, Specs Written (Plans Pending)

### Verified-clean surfaces

- `lexigram-testing`'s fakes — reviewed and confirmed clean; no findings.
- Fernet encryption usage — confirmed consistent.
"""

STATUS_COLUMN_SAMPLE = """\
| # | Area | Severity mix | Spec | Plan | Status |
|---|------|--------------|------|------|--------|
| 7 | **XSS / output rendering** | Critical \u00d72, High \u00d75, Med \u00d71 | `specs/x.md` | `plans/x.md` | Done |
| 8 | **Secrets / credentials** | Critical \u00d71 | `specs/y.md` | `plans/y.md` | Open |
"""


def test_parse_tracker_rows_handles_five_and_six_column_rows() -> None:
    rows = parse_tracker_rows(SAMPLE)
    assert [row.number for row in rows] == [1, 26, 50]
    row1, row26, row50 = rows
    assert row1.area == "**P0 session-secret**"
    assert row1.severity_mix == "Critical \u00d73"
    assert row1.status.startswith("`plans/")
    assert not hasattr(row1, "spec")
    assert not hasattr(row1, "plan")
    assert row26.severity_mix == "High \u00d71"  # six-column row: §28 ref dropped
    assert row50.status == "Not yet written"


def test_parse_tracker_rows_uses_status_column_without_plan_text() -> None:
    rows = parse_tracker_rows(STATUS_COLUMN_SAMPLE)
    assert [row.number for row in rows] == [7, 8]
    assert rows[0].status.endswith("Done")
    assert rows[1].status.endswith("Open")
    assert "specs/" not in rows[0].status


def test_row_is_done() -> None:
    rows = parse_tracker_rows(SAMPLE)
    assert row_is_done(rows[0]) is True
    assert row_is_done(rows[1]) is True
    assert row_is_done(rows[2]) is False


def test_row_is_done_reads_status_column() -> None:
    rows = parse_tracker_rows(STATUS_COLUMN_SAMPLE)
    assert row_is_done(rows[0]) is True
    assert row_is_done(rows[1]) is False


def test_parse_verified_clean_extracts_bullets() -> None:
    assert parse_verified_clean(SAMPLE) == (
        "`lexigram-testing`'s fakes — reviewed and confirmed clean; no findings.",
        "Fernet encryption usage — confirmed consistent.",
    )


def test_severity_counts_normalizes_medium() -> None:
    assert severity_counts(
        "Critical \u00d73, High \u00d72, Med \u00d72, Low \u00d72"
    ) == {
        "Critical": 3,
        "High": 2,
        "Med": 2,
        "Low": 2,
    }
    assert severity_counts("Medium \u00d71") == {"Med": 1}
    assert severity_counts("") == {}
