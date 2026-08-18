from __future__ import annotations

from pathlib import Path

from dev.audit.generators.base import MarkdownAuditGenerator
from dev.core.rule_engine import RuleSeverity, run_rules
from dev.core.rules_catalog import build_rules_catalog

RULE_RESOLUTION_GUIDE: dict[str, str] = {
    "no-cross-extension-import": (
        "Move shared contracts to `lexigram-contracts`, register implementations via providers, "
        "and resolve dependencies through the container instead of direct extension imports."
    ),
    "import-absolute-only": (
        "Replace relative imports (for example `from .module import ...`) with absolute imports rooted at "
        "`lexigram...` so module ownership stays explicit."
    ),
    "init-no-logic": (
        "Keep `__init__.py` export-only. Move functions/classes to dedicated modules and re-export symbols "
        "through `__all__` from `__init__.py`."
    ),
    "enum-must-use-enum": (
        "Convert pseudo-enum constant classes to real enums (for example `class X(str, Enum)`) so callers "
        "get type-safe membership, iteration, and validation."
    ),
    "python-syntax-error": (
        "Fix syntax so the rule scanner can parse the file. Audit results are incomplete while parse failures remain."
    ),
    "sec-tls-verify-disabled": (
        "Re-enable certificate verification (use `ssl.create_default_context()` and never "
        "pass `verify=False`); if a test environment needs it, gate it behind a config flag."
    ),
    "sec-hardcoded-secret": (
        "Move the literal secret to environment configuration and resolve it via the "
        "framework's config/secrets stores."
    ),
    "sec-cors-wildcard-credentials": (
        "Replace the `*` origin with an explicit allow-list when credentials are enabled."
    ),
    "sec-jwt-verification-disabled": (
        "Keep signature verification on; pin `algorithms` to the signed algorithms and never "
        "set `verify_signature=False`."
    ),
}


class RulesAuditGenerator(MarkdownAuditGenerator):
    """Generate a markdown audit for Lexigram architectural rule violations."""

    name = "rules"
    description = "Generate AUDIT_RULES.md from Lexigram architectural rule checks."
    output_file = "AUDIT_RULES.md"

    def render_markdown(self, *, root: Path) -> str:
        """Render the rules audit markdown for the requested workspace root."""

        all_mode = getattr(self, "_all_mode", False)
        packages = None if all_mode else tuple(
            p.name for p in self.iter_package_roots(root=root)
        )
        result = run_rules(root, packages=packages)
        rules_catalog = {rule.rule_id: rule for rule in build_rules_catalog()}
        counts = {
            severity: sum(1 for finding in result.findings if finding.severity is severity)
            for severity in RuleSeverity
        }
        findings_by_rule: dict[str, int] = {}
        for finding in result.findings:
            findings_by_rule[finding.rule_id] = findings_by_rule.get(finding.rule_id, 0) + 1

        markdown = """# AUDIT_RULES.md — Lexigram Framework Rules Audit

> **Source**: Static rule analysis for architectural boundaries, import policy, and package coverage.

---

## Severity Summary

| Severity | Count |
|----------|-------|
"""
        for severity in (RuleSeverity.CRITICAL, RuleSeverity.IMPORTANT, RuleSeverity.MINOR):
            markdown += f"| {severity.value} | {counts[severity]} |\n"

        markdown += "\n## Findings\n\n"
        markdown += "| File | Line | Rule ID | Severity | Message |\n"
        markdown += "|------|------|---------|----------|---------|\n"
        if result.findings:
            for finding in result.findings:
                markdown += (
                    f"| `{finding.path.as_posix()}` | {finding.line} | `{finding.rule_id}` | "
                    f"`{finding.severity.value}` | {_escape_cell(finding.message)} |\n"
                )
        else:
            markdown += "| `(none)` | 0 | `none` | `none` | No rule violations found. |\n"

        markdown += "\n## Rule Diagnostics\n\n"
        markdown += "| Rule ID | Severity | Findings | Detected Error About |\n"
        markdown += "|---------|----------|----------|----------------------|\n"
        for rule_id in sorted(findings_by_rule):
            sample_finding = next(f for f in result.findings if f.rule_id == rule_id)
            detected_error_about = rules_catalog.get(rule_id, sample_finding).rationale
            markdown += (
                f"| `{rule_id}` | `{sample_finding.severity.value}` | {findings_by_rule[rule_id]} | "
                f"{_escape_cell(detected_error_about)} |\n"
            )

        markdown += "\n## Package Coverage\n\n"
        markdown += f"- Discovered packages: {len(result.coverage.discovered_packages)}\n"
        markdown += f"- Covered packages: {len(result.coverage.covered_packages)}\n"
        markdown += f"- Missing packages: {len(result.coverage.missing_packages)}\n"
        markdown += f"- Coverage status: **{'PASS' if result.coverage.success else 'FAIL'}**\n\n"
        markdown += "### Covered Packages\n\n"
        if result.coverage.covered_packages:
            for package_name in sorted(result.coverage.covered_packages):
                markdown += f"- `{package_name}`\n"
        else:
            markdown += "- `(none)`\n"
        markdown += "\n### Missing Packages\n\n"
        if result.coverage.missing_packages:
            for package_name in sorted(result.coverage.missing_packages):
                markdown += f"- `{package_name}`\n"
        else:
            markdown += "- `(none)`\n"
        markdown += "\n## Resolution Guide\n\n"
        if findings_by_rule:
            for rule_id in sorted(findings_by_rule):
                resolution = RULE_RESOLUTION_GUIDE.get(
                    rule_id,
                    "Review the rule finding context and align implementation to Lexigram architecture boundaries.",
                )
                markdown += f"- `{rule_id}`: {resolution}\n"
        else:
            markdown += "- No resolutions needed. No rule findings detected.\n"
        markdown += "\n"
        return markdown


def _escape_cell(value: str) -> str:
    """Escape markdown table control characters inside cell content."""

    return value.replace("|", "\\|").replace("\n", " ")
