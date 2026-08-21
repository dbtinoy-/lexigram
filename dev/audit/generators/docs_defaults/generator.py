"""Audit generator: verify prose default-value claims in package docs.

Covers the claim classes the env-var/priority audit cannot see — literal
defaults stated in docs:

1. **Config-table ``Default`` columns** — rows whose key (or ``Env Var`` cell)
   resolves to a config field are checked against the field's real default.
2. **Inline claims** — ``KEY (default: VALUE)`` / ``KEY (default=VALUE)``.
3. **Prose** — ``KEY defaults to VALUE`` / ``KEY default is VALUE``.

An identified key is verified ONLY when it resolves to a unique config field
with a comparable literal default; ambiguous keys, unparseable values, and
``default_factory``/required fields are counted as unverifiable and never
flagged as findings.

Implementation lives across :mod:`universe` (real config-default index)
and :mod:`claims` (claim parsing/comparison); this module holds the
generator that drives both.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dev.audit.generators.base import AuditRunResult, MarkdownAuditGenerator
from dev.audit.generators.docs_claims import _build_env_validity
from dev.audit.generators.docs_defaults.claims import (
    _defaults_equal,
    _doc_class_hints,
    _iter_claims,
    _parse_claim_value,
    _unique_comparable_default,
)
from dev.audit.generators.docs_defaults.universe import (
    _build_universe,
    DefaultUniverse,
)


@dataclass(frozen=True, slots=True)
class DefaultIssue:
    """A doc default claim that disagrees with the framework's actual default."""

    doc: str
    claim: str
    claimed: str
    expected: str


class DocsDefaultsAuditGenerator(MarkdownAuditGenerator):
    """Audit doc default-value claims (tables, inline, prose) against config classes."""

    name = "docs-defaults"
    description = (
        "Generate AUDIT_DOC_DEFAULTS.md verifying that every default-value claim "
        "(config-table Default columns, inline `(default: X)`, prose `defaults to`) "
        "in package docs matches the config class's actual default."
    )
    output_file = "AUDIT_DOC_DEFAULTS.md"

    def run(
        self,
        *,
        root: Path | None = None,
        all_mode: bool = False,
    ) -> AuditRunResult:
        """Execute the defaults audit and fail when any claim mismatches."""
        validation = self.validate(root=root)
        if not validation.success:
            return validation
        resolved_root = self.resolve_root(root)
        output_dir = (
            resolved_root if all_mode else resolved_root / "docs/audit"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown, issue_count = self._render(resolved_root)
        output_path = output_dir / self.output_file
        output_path.write_text(markdown, encoding="utf-8")
        status = (
            "PASS" if issue_count == 0 else f"{issue_count} mismatched default claim(s)"
        )
        return AuditRunResult(
            name=self.name,
            success=issue_count == 0,
            message=f"{status} -> wrote {output_path.name}",
            output_path=output_path,
        )

    def render_markdown(self, *, root: Path) -> str:
        """Render the defaults audit report (protocol compatibility)."""
        return self._render(root)[0]

    def _render(self, root: Path) -> tuple[str, int]:
        validity = _build_env_validity()
        universe = DefaultUniverse(validity, _build_universe())

        verified = 0
        unverifiable = 0
        issues: list[DefaultIssue] = []
        for package in self.iter_package_roots(root=root):
            docs_dir = package / "docs"
            if not docs_dir.is_dir():
                continue
            for md_file in sorted(docs_dir.glob("*.md")):
                try:
                    text = md_file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                rel = md_file.relative_to(root).as_posix()
                table_claims, prose_claims = _iter_claims(text)
                hints = _doc_class_hints(text)
                for key, claimed in table_claims + prose_claims:
                    claimed_value: object
                    ok, parsed = _parse_claim_value(claimed)
                    if not ok:
                        unverifiable += 1
                        continue
                    claimed_value = parsed
                    candidates = universe.resolve(key)
                    if not candidates:
                        unverifiable += 1
                        continue
                    unambiguous, real_default, comparable = _unique_comparable_default(
                        candidates, hints
                    )
                    if not unambiguous:
                        unverifiable += 1
                        continue
                    equal = _defaults_equal(claimed_value, real_default)
                    if equal is None:
                        unverifiable += 1
                        continue
                    if equal:
                        verified += 1
                        continue
                    expected = f"{comparable[0].class_name}.{comparable[0].field}={real_default!r}"
                    issues.append(
                        DefaultIssue(
                            doc=rel,
                            claim=f"{key} -> {claimed}",
                            claimed=repr(claimed_value),
                            expected=expected,
                        )
                    )

        lines = [
            "# AUDIT_DOC_DEFAULTS.md — Lexigram Documentation Default Claims Audit",
            "",
            "> **Source**: Every default-value claim in every package `docs/*.md` file",
            "> (config-table `Default` columns, inline `(default: X)`, prose `defaults to`)",
            "> resolved against the framework's config classes. Claims whose key is",
            "> ambiguous, whose value is not a comparable literal, or whose field has",
            "> no static default are counted unverifiable — never flagged.",
            "",
            "## Summary",
            "",
            f"- Default claims verified: {verified}",
            f"- Unverifiable claims (skipped): {unverifiable}",
            f"- Mismatched claims: {len(issues)}",
            "",
        ]

        if issues:
            lines.append("## Mismatched Claims")
            lines.append("")
            lines.append("| Doc | Claim | Claimed | Expected (class.field=default) |")
            lines.append("|-----|-------|---------|-------------------------------|")
            for issue in sorted(issues, key=lambda i: (i.doc, i.claim)):
                lines.append(
                    f"| `{issue.doc}` | `{issue.claim}` | {issue.claimed} | `{issue.expected}` |"
                )
            lines.append("")
        else:
            lines.append("No mismatched default claims detected.")
            lines.append("")

        return "\n".join(lines), len(issues)


__all__ = ["DocsDefaultsAuditGenerator"]
