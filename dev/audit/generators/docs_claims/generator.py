"""Audit generator: verify claim-level API facts cited across package docs.

Checks two claim classes that the import audit cannot see:

1. **Environment variables** — every ``LEX_*`` env var mention in a package doc
   must resolve against live configuration classes:

   - ``LEX_<SECTION>__<KEY>`` — core ``LEX_`` prefix plus a ``*Config`` class
     section and (nested) key path, e.g. ``LEX_LOGGING__JSON_FORMAT``.
   - ``LEX_<PACKAGE>__<KEY>`` — extension packages register their own prefix
     (e.g. ``LEX_SQL``) with keys straight from their config classes, e.g.
     ``LEX_SQL__BACKEND__URL``.
   - ``<env_prefix>`` — pydantic ``model_config["env_prefix"]`` families, e.g.
     ``LEX_NOTIFICATION__INBOX__MARK_READ_ON_FETCH``.
   - ``*`` keypath segments are wildcards for list/dict positions
     (``LEX_CACHE__BACKENDS__0__NAME`` matches ``backends.*.name``).
   - Variables read directly by framework code (``os.environ.get("LEX_QUIET")``)
     are whitelisted.
   - ``LEX_ERR_*`` is the error-code namespace, not env vars — ignored.
   - Trailing-``__`` tokens are env-source prefix claims.

2. **Provider priorities** — every ``ProviderPriority.<MEMBER>`` claim must be a
   real member of ``lexigram.contracts.core.provider.ProviderPriority``.

Implementation: :mod:`introspect` (config-class typing helpers),
:mod:`registry` (discovery + env-validity maps), :mod:`claims` (claim
extraction/verification), and this module's generator class.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path

from dev.audit.generators.base import AuditRunResult, MarkdownAuditGenerator
from dev.audit.generators.docs_claims._constants import (
    _PRIORITY_ENUM,
    _PRIORITY_MODULE,
)
from dev.audit.generators.docs_claims.claims import (
    _collect_env_claims,
    _collect_priority_claims,
    _verify_env_var,
)
from dev.audit.generators.docs_claims.registry import (
    _build_declared_prefixes,
    _build_direct_reads,
    _build_env_validity,
)


@dataclass(frozen=True, slots=True)
class ClaimIssue:
    """A doc claim that did not resolve against the framework."""

    doc: str
    claim: str
    reason: str


class DocsClaimsAuditGenerator(MarkdownAuditGenerator):
    """Audit env-var and priority claims in package docs against the framework."""

    name = "docs-claims"
    description = (
        "Generate AUDIT_DOC_CLAIMS.md verifying that every `LEX_*` env var and "
        "`ProviderPriority.*` claim in package docs resolves against the framework."
    )
    output_file = "AUDIT_DOC_CLAIMS.md"

    def run(
        self,
        *,
        root: Path | None = None,
        all_mode: bool = False,
    ) -> AuditRunResult:
        """Execute the claims audit and fail when any claim does not resolve."""
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
        status = "PASS" if issue_count == 0 else f"{issue_count} unresolved claim(s)"
        return AuditRunResult(
            name=self.name,
            success=issue_count == 0,
            message=f"{status} -> wrote {output_path.name}",
            output_path=output_path,
        )

    def render_markdown(self, *, root: Path) -> str:
        """Render the claims audit report (protocol compatibility)."""
        return self._render(root)[0]

    def _render(self, root: Path) -> tuple[str, int]:
        """Build the report body and count unresolved claims."""
        validity = _build_env_validity()
        direct = _build_direct_reads()
        declared = _build_declared_prefixes()
        try:
            priority_mod = importlib.import_module(_PRIORITY_MODULE)
            priority_members = set(getattr(priority_mod, _PRIORITY_ENUM).__members__)
        except Exception:  # noqa: BLE001 - surfaced in the report
            priority_members = set()

        issues: list[ClaimIssue] = []
        verified_vars = 0
        verified_prios = 0
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
                for token in _collect_env_claims(text):
                    ok, desc = _verify_env_var(token, validity, direct, declared)
                    if ok:
                        if desc:
                            verified_vars += 1
                        continue
                    issues.append(
                        ClaimIssue(doc=rel, claim=token, reason=f"env var: {desc}")
                    )
                for member in _collect_priority_claims(text):
                    if member in priority_members:
                        verified_prios += 1
                        continue
                    issues.append(
                        ClaimIssue(
                            doc=rel,
                            claim=f"ProviderPriority.{member}",
                            reason="no such member on lexigram.contracts.core.provider.ProviderPriority",
                        )
                    )

        lines = [
            "# AUDIT_DOC_CLAIMS.md — Lexigram Documentation Claims Audit",
            "",
            "> **Source**: Every `LEX_*` env var and `ProviderPriority.*` mention in every",
            "> package `docs/*.md` file (prose + python blocks), resolved against the",
            "> installed framework. Env vars must map to a real `*Config` field",
            "> (`LEX_<SECTION>__<KEY>` / `LEX_<PACKAGE>__<KEY>`) or be read directly by",
            "> framework code.",
            "",
            "## Summary",
            "",
            f"- Env vars verified: {verified_vars}",
            f"- Priorities verified: {verified_prios}",
            f"- Unresolved claims: {len(issues)}",
            "",
        ]

        if issues:
            lines.append("## Unresolved Claims")
            lines.append("")
            lines.append("| Doc | Claim | Reason |")
            lines.append("|-----|-------|--------|")
            for issue in sorted(issues, key=lambda i: (i.doc, i.claim)):
                lines.append(f"| `{issue.doc}` | `{issue.claim}` | {issue.reason} |")
            lines.append("")
        else:
            lines.append("No unresolved doc claims detected.")
            lines.append("")

        return "\n".join(lines), len(issues)


__all__ = ["DocsClaimsAuditGenerator"]
