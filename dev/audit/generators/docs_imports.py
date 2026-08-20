"""Audit generator: verify every ``lexigram.*`` import cited in package docs resolves.

Scans every ``docs/*.md`` file under each ``lexigram`` / ``lexigram-*`` package and
checks that each ``from lexigram... import ...`` / ``import lexigram...`` statement
inside a fenced python block resolves at runtime — the module must import and every
imported attribute must exist. Placeholder domain names from examples (e.g. an
``EmailConfig`` that lives inside the user's app) are deliberately ignored because
they never carry a ``lexigram.*`` module path.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
import re

from dev.audit.generators.base import AuditRunResult, MarkdownAuditGenerator

_PYTHON_FENCE_RE = re.compile(r"```(?:python|py)\s*\n(.*?)```", re.DOTALL)

# `from <lexigram module> import <names>` — names may be parenthesized across lines.
_FROM_IMPORT_RE = re.compile(
    r"^\s*from\s+(lexigram(?:\.\w+)*)\s+import\s+(.*)$", re.MULTILINE
)
# `import lexigram.module[.module]` — plain module import.
_PLAIN_IMPORT_RE = re.compile(r"^\s*import\s+(lexigram(?:\.\w+)+)\s*$", re.MULTILINE)
_NAME_START = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True, slots=True)
class DocImport:
    """One ``lexigram.*`` import statement found in a doc's python block."""

    module: str
    names: tuple[str, ...]
    statement: str


@dataclass(frozen=True, slots=True)
class ImportIssue:
    """An import that failed to resolve, plus where it lives."""

    doc: str
    statement: str
    reason: str


def _iter_python_blocks(md_text: str) -> tuple[str, ...]:
    return tuple(match.group(1) for match in _PYTHON_FENCE_RE.finditer(md_text))


def _split_names(raw: str) -> tuple[str, ...]:
    """Split an import target clause into plain names, dropping aliases."""
    if raw.startswith("("):
        raw = raw[1:]
        if ")" not in raw:
            return ()
        raw = raw.split(")", 1)[0]
    names: list[str] = []
    for bit in raw.replace("\\", " ").split(","):
        bit = bit.strip()
        if not bit:
            continue
        plain = bit.split(" as ", 1)[0].strip()
        match = _NAME_START.match(plain)
        if match is not None:
            names.append(match.group(0))
    return tuple(dict.fromkeys(names))


def _collect_imports(md_text: str) -> tuple[DocImport, ...]:
    """Collect every ``lexigram.*`` import from the doc's python blocks.

    Blocks are truncated at the first line containing a ``❌`` marker — the
    convention for deliberately-wrong anti-examples (e.g. PUBLIC_API.md's
    "❌ Internal — avoid deep paths" snippet) — so those never count as issues.
    """
    imports: list[DocImport] = []
    for block in _iter_python_blocks(md_text):
        cut = block.find("❌")
        if cut != -1:
            block = block[:cut]
        for match in _FROM_IMPORT_RE.finditer(block):
            module, raw = match.group(1), match.group(2)
            names = _split_names(raw)
            imports.append(
                DocImport(
                    module=module,
                    names=names,
                    statement=f"from {module} import ... ({len(names)} names)",
                )
            )
        for match in _PLAIN_IMPORT_RE.finditer(block):
            module = match.group(1)
            imports.append(
                DocImport(module=module, names=(), statement=f"import {module}")
            )
    return tuple(imports)


def _verify(imp: DocImport) -> str | None:
    """Return a failure reason, or None when the import statement resolves."""
    try:
        module = importlib.import_module(imp.module)
    except Exception as exc:  # noqa: BLE001 - surfaced in the audit report
        return f"module import failed: {exc}"
    missing: list[str] = []
    for name in imp.names:
        try:
            present = hasattr(module, name)
        except Exception as exc:  # noqa: BLE001 - lazy __getattr__ may raise
            missing.append(f"{name} (attribute probe raised {exc})")
            continue
        if not present:
            missing.append(name)
    if missing:
        return f"missing name(s) {', '.join(missing)} on {imp.module}"
    return None


class DocsImportsAuditGenerator(MarkdownAuditGenerator):
    """Audit every ``lexigram.*`` import in package docs against the live package."""

    name = "docs-imports"
    description = (
        "Generate AUDIT_DOC_IMPORTS.md by resolving every `lexigram.*` import "
        "cited in package docs python blocks against the installed framework."
    )
    output_file = "AUDIT_DOC_IMPORTS.md"

    def run(
        self,
        *,
        root: Path | None = None,
        all_mode: bool = False,
    ) -> AuditRunResult:
        """Execute the import audit and fail when any import does not resolve."""
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
        status = "PASS" if issue_count == 0 else f"{issue_count} unresolved import(s)"
        return AuditRunResult(
            name=self.name,
            success=issue_count == 0,
            message=f"{status} -> wrote {output_path.name}",
            output_path=output_path,
        )

    def render_markdown(self, *, root: Path) -> str:
        """Render the import audit report (protocol compatibility)."""
        return self._render(root)[0]

    def _render(self, root: Path) -> tuple[str, int]:
        """Build the report body and count unresolved imports."""
        issues: list[ImportIssue] = []
        verified = 0
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
                for imp in _collect_imports(text):
                    reason = _verify(imp)
                    if reason is None:
                        verified += 1
                    else:
                        issues.append(
                            ImportIssue(doc=rel, statement=imp.statement, reason=reason)
                        )

        by_doc: dict[str, list[ImportIssue]] = {}
        for issue in sorted(issues, key=lambda i: (i.doc, i.statement)):
            by_doc.setdefault(issue.doc, []).append(issue)

        lines = [
            "# AUDIT_DOC_IMPORTS.md — Lexigram Documentation Import Audit",
            "",
            "> **Source**: Every `lexigram.*` `from`/`import` statement in the python",
            "> blocks of every package `docs/*.md` file, resolved against the installed",
            "> framework with `importlib`. An import fails when its module cannot be",
            "> imported or when an imported name is missing from that module.",
            "",
            "## Summary",
            "",
            f"- Imports verified: {verified}",
            f"- Unresolved imports: {len(issues)}",
            "",
        ]

        if issues:
            lines.append("## Unresolved Imports")
            lines.append("")
            lines.append("| Doc | Import | Reason |")
            lines.append("|-----|--------|--------|")
            for issue in sorted(issues, key=lambda i: (i.doc, i.statement)):
                lines.append(
                    f"| `{issue.doc}` | `{issue.statement}` | {issue.reason} |"
                )
            lines.append("")
        else:
            lines.append("No unresolved `lexigram.*` imports detected.")
            lines.append("")

        return "\n".join(lines), len(issues)


__all__ = ["DocsImportsAuditGenerator"]
