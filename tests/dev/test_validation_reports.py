"""Tests for rules-report summary parsing."""

from __future__ import annotations

from dev.core.validation import parse_rules_report_summary

_RULES_REPORT = """# AUDIT_RULES.md — Lexigram Framework Rules Audit

## Severity Summary

| Severity | Count |
|----------|-------|
| critical | 2 |
| important | 3 |
| minor | 1 |

## Findings

| File | Line | Rule ID | Severity | Message |
|------|------|---------|----------|---------|
| `a/b.py` | 5 | `no-cross-extension-import` | `critical` | msg |
| `c/d.py` | 8 | `no-cross-extension-import` | `critical` | msg |
| `e/f.py` | 1 | `init-no-logic` | `important` | msg |

## Package Coverage

- Discovered packages: 2
- Covered packages: 2
- Missing packages: 0
- Coverage status: **PASS**

### Covered Packages

- `lexigram-demo-a`
- `lexigram-demo-b`

### Missing Packages

- `(none)`

## Resolution Guide

- `no-cross-extension-import`: Move shared contracts to `lexigram-contracts`.
- `init-no-logic`: Keep `__init__.py` export-only.
"""


def test_parse_rules_report_summary_counts_severities_and_top_rules() -> None:
    summary = parse_rules_report_summary(_RULES_REPORT)

    assert summary.critical == 2
    assert summary.important == 3
    assert summary.minor == 1
    assert summary.top_misalignments[0].rule_id == "no-cross-extension-import"
    assert summary.top_misalignments[0].count == 2


def test_parse_rules_report_summary_does_not_mix_resolution_guide_into_missing_packages() -> None:
    summary = parse_rules_report_summary(_RULES_REPORT)

    # The Resolution Guide bullets must not leak into the missing-package list.
    assert summary.missing_packages == ()
    assert summary.coverage_status is True
    assert summary.discovered_packages == 2
    assert summary.covered_packages == 2


def test_parse_rules_report_summary_keeps_real_missing_packages() -> None:
    report = _RULES_REPORT.replace("- `(none)`", "- `lexigram-nope`")
    summary = parse_rules_report_summary(report)

    assert summary.missing_packages == ("lexigram-nope",)