from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from dev.audit.generators.base import AuditRunResult, MarkdownAuditGenerator
from dev.core.package_inventory import discover_package_paths

# Internal link forms: ](/section/name/) or ](/section/name/#anchor)
_LINK_RE = re.compile(r"\]\((/[^)\s]+?)\)")

# Heading anchors in the target file: "## Provider Priorities" -> provider-priorities
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")


@dataclass(frozen=True, slots=True)
class LinkFinding:
    """A single internal link occurrence inside the docs corpus."""

    source_file: str
    target: str
    anchor: str | None
    line: int


def _iter_internal_links(docs_root: Path) -> tuple[LinkFinding, ...]:
    """Collect all internal absolute links from markdown files under a docs root."""

    findings: list[LinkFinding] = []
    for md_file in sorted(docs_root.rglob("*.md")):
        if md_file.name == "README.md":
            continue
        try:
            lines = md_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, start=1):
            for match in _LINK_RE.finditer(line):
                raw = match.group(1)
                target, _, anchor = raw.partition("#")
                findings.append(
                    LinkFinding(
                        source_file=md_file.relative_to(docs_root).as_posix(),
                        target=target,
                        anchor=anchor or None,
                        line=line_number,
                    )
                )
    return tuple(findings)


def _resolve_target(target: str, *, docs_root: Path, repo_root: Path) -> bool:
    """Return True when an absolute link target resolves on disk."""

    parts = [part for part in target.split("/") if part]

    # /packages/<package>/ routes to the package's own docs/ folder.
    if parts and parts[0] == "packages":
        if len(parts) == 1:
            return True  # /packages/ is a virtual site index, not a file
        package_name = parts[1] if len(parts) > 1 else ""
        package_dir = _find_package_dir(package_name, repo_root)
        return package_dir is not None and (package_dir / "docs").is_dir()

    if not parts:
        return False

    section = parts[0]
    page = parts[1] if len(parts) > 1 else "index"

    candidates = (
        docs_root / section / f"{page}.md",
        docs_root / section / page / "index.md",
        docs_root / section / "index.md",
    )
    return any(candidate.is_file() for candidate in candidates)


def _find_package_dir(package_name: str, repo_root: Path) -> Path | None:
    """Locate a workspace member package directory, anywhere in the tree."""

    for relative in discover_package_paths(repo_root):
        if relative.name == package_name:
            return repo_root / relative
    return None


def _resolve_anchor(target_path: Path | None, anchor: str | None) -> bool:
    """Return True when the heading anchor exists in the target file."""

    if target_path is None or not anchor:
        return True
    try:
        lines = target_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    wanted = _normalize_anchor(anchor)
    for line in lines:
        heading = _HEADING_RE.match(line)
        if heading is None:
            continue
        if _normalize_anchor(heading.group(1)) == wanted:
            return True
    return False


def _normalize_anchor(value: str) -> str:
    """Normalize a heading or anchor fragment to the Starlight/GitHub slug."""

    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _target_path(target: str, *, docs_root: Path, repo_root: Path) -> Path | None:
    """Return the on-disk file a link target resolves to, if any."""

    parts = [part for part in target.split("/") if part]
    if not parts:
        return None
    if parts[0] == "packages":
        if len(parts) == 1:
            return None  # virtual site index — no file to anchor-check
        package_name = parts[1] if len(parts) > 1 else ""
        package_dir = _find_package_dir(package_name, repo_root)
        if package_dir is None:
            return None
        index = package_dir / "docs" / "index.md"
        return index if index.is_file() else None
    section = parts[0]
    page = parts[1] if len(parts) > 1 else "index"
    for candidate in (
        docs_root / section / f"{page}.md",
        docs_root / section / page / "index.md",
        docs_root / section / "index.md",
    ):
        if candidate.is_file():
            return candidate
    return None


class DocsLinksAuditGenerator(MarkdownAuditGenerator):
    """Audit internal links inside the docs corpus for dead targets."""

    name = "docs-links"
    description = (
        "Generate AUDIT_DOC_LINKS.md from internal markdown links in "
        "docs/lexigram-docs, reporting dead targets and anchors."
    )
    output_file = "AUDIT_DOC_LINKS.md"

    def run(
        self,
        *,
        root: Path | None = None,
        all_mode: bool = False,
    ) -> AuditRunResult:
        """Execute the link audit and fail when dead links are found."""

        validation = self.validate(root=root)
        if not validation.success:
            return validation
        resolved_root = self.resolve_root(root)
        output_dir = resolved_root if all_mode else resolved_root / "docs/lexigram-docs/audit"
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown, dead_count = self._render(resolved_root)
        output_path = output_dir / self.output_file
        output_path.write_text(markdown, encoding="utf-8")
        status = "PASS" if dead_count == 0 else f"{dead_count} dead link(s)"
        return AuditRunResult(
            name=self.name,
            success=dead_count == 0,
            message=f"{status} -> wrote {output_path.name}",
            output_path=output_path,
        )

    def render_markdown(self, *, root: Path) -> str:
        """Render the docs-links audit report (protocol compatibility)."""

        return self._render(root)[0]

    def _render(self, root: Path) -> tuple[str, int]:
        """Build the report body and count dead links."""

        docs_root = root / "docs/lexigram-docs"
        findings = _iter_internal_links(docs_root)

        rows: list[tuple[LinkFinding, bool, bool]] = []
        for finding in findings:
            target_exists = _resolve_target(finding.target, docs_root=docs_root, repo_root=root)
            target_path = _target_path(finding.target, docs_root=docs_root, repo_root=root)
            anchor_exists = _resolve_anchor(target_path, finding.anchor)
            rows.append((finding, target_exists, anchor_exists))

        dead = [row for row in rows if not row[1] or not row[2]]
        total_links = len(rows)

        lines = [
            "# AUDIT_DOC_LINKS.md — Lexigram Documentation Link Audit",
            "",
            "> **Source**: Internal markdown links inside `docs/lexigram-docs/`.",
            "> A link is *dead* when its target file does not exist, when a",
            "> `/packages/<name>/` route points at a package without a `docs/`",
            "> folder, or when its heading anchor is missing from the target.",
            "",
            "## Summary",
            "",
            f"- Internal links scanned: {total_links}",
            f"- Dead links: {len(dead)}",
            "",
        ]

        if dead:
            lines.append("## Dead Links")
            lines.append("")
            lines.append("| Source | Line | Target | Problem |")
            lines.append("|--------|-----:|--------|---------|")
            for finding, target_exists, _anchor_exists in sorted(
                dead, key=lambda row: (row[0].target, row[0].source_file)
            ):
                problem = (
                    "target not found"
                    if not target_exists
                    else f"anchor `#{finding.anchor}` not found"
                )
                lines.append(
                    f"| `{finding.source_file}` | {finding.line} | "
                    f"`{finding.target}` | {problem} |"
                )
            lines.append("")
        else:
            lines.append("No dead internal links detected.")
            lines.append("")

        return "\n".join(lines), len(dead)
