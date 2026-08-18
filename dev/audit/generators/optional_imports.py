from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import re
import sys
import tomllib

from dev.audit.generators.base import AuditRunResult, MarkdownAuditGenerator

_VERSION_SPEC_RE = re.compile(r"[\[,<>=!~;]")

# Import module root -> distribution name(s), normalized with '-' separators.
ALIASES: dict[str, tuple[str, ...]] = {
    "PIL": ("pillow",),
    "cv2": ("opencv-python",),
    "dotenv": ("python-dotenv",),
    "IPython": ("ipython",),
    "jose": ("python-jose",),
    "jwt": ("pyjwt",),
    "argon2": ("argon2-cffi",),
    "saml2": ("pysaml2",),
    "yaml": ("pyyaml",),
    "strawberry": ("strawberry-graphql",),
    "google.cloud.pubsub": ("google-cloud-pubsub",),
    "google.cloud.storage": ("google-cloud-storage",),
    "azure.storage.blob": ("azure-storage-blob",),
    "azure.identity": ("azure-identity",),
    "gcloud.aio.storage": ("gcloud-aio-storage",),
    "botocore": ("aiobotocore", "botocore"),
    "prometheus_client": ("prometheus-client",),
    "qdrant_client": ("qdrant-client",),
    "weaviate_client": ("weaviate-client",),
    "pinecone": ("pinecone-client",),
    "aio_pika": ("aio-pika",),
    "slack_sdk": ("slack-sdk",),
    "sklearn": ("scikit-learn",),
    "typing_extensions": ("typing-extensions",),
    "opentelemetry": (
        "opentelemetry-api",
        "opentelemetry-sdk",
        "opentelemetry-exporter-otlp",
    ),
}

# Distribution name -> candidate import roots (for unused-extra detection).
REVERSE_ALIASES: dict[str, tuple[str, ...]] = {}
for _import_root, _dist_names in ALIASES.items():
    for _dist_name in _dist_names:
        existing = REVERSE_ALIASES.get(_dist_name, ())
        REVERSE_ALIASES[_dist_name] = (*existing, _import_root)


@dataclass(frozen=True, slots=True)
class ImportFinding:
    """A third-party module-level import in a package source file."""

    module: str
    dotted: str | None
    file: str
    line: int
    guarded: bool
    type_only: bool


@dataclass(frozen=True, slots=True)
class DependencyDeclarations:
    """Declared base and optional dependencies of a package."""

    base: frozenset[str] = frozenset()
    optional: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class PackageAudit:
    """Audit result for a single package."""

    name: str
    declarations: DependencyDeclarations
    findings: tuple[ImportFinding, ...]
    unused_extras: tuple[str, ...]

    @property
    def violations(self) -> int:
        return sum(1 for finding in self.findings if _is_violation(finding, self.declarations))


def _normalize_dep(name: str) -> str:
    """Normalize a distribution name to 'dash-separated lowercase'."""

    return name.replace("_", "-").lower()


def _declared_dist_names(raw_deps: Iterable[object]) -> set[str]:
    """Extract normalized distribution names from dependency strings."""

    names: set[str] = set()
    for raw in raw_deps:
        if not isinstance(raw, str):
            continue
        base = _VERSION_SPEC_RE.split(raw, maxsplit=1)[0].strip()
        if base:
            names.add(_normalize_dep(base))
    return names


def _parse_pyproject(path: Path) -> DependencyDeclarations:
    """Parse base and optional dependencies from a package pyproject.toml."""

    with path.open("rb") as handle:
        data = tomllib.load(handle)
    project = data.get("project", {})
    optional: set[str] = set()
    for raw_group in project.get("optional-dependencies", {}).values():
        if isinstance(raw_group, list):
            optional |= _declared_dist_names(raw_group)
    return DependencyDeclarations(
        base=frozenset(_declared_dist_names(project.get("dependencies", ()))),
        optional=frozenset(optional),
    )


def _is_stdlib(module: str) -> bool:
    """Return True when the import root is a standard-library module."""

    return module in sys.stdlib_module_names


def _is_lexigram(module: str) -> bool:
    """Return True when the import root belongs to the lexigram workspace."""

    return module == "lexigram" or module.startswith("lexigram-")


def _strip_import(node: ast.Import | ast.ImportFrom) -> str:
    """Return the top-level module root imported by an AST node."""

    source = node.names[0].name if isinstance(node, ast.Import) else node.module or ""
    return source.split(".")[0]


def _strip_import_dotted(node: ast.Import | ast.ImportFrom) -> str:
    """Return the full dotted module path imported by an AST node."""

    return node.names[0].name if isinstance(node, ast.Import) else node.module or ""


def _is_type_checking_guard(node: ast.If) -> bool:
    """Return True for a guard like ``if TYPE_CHECKING:``."""

    return isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING"


def _scan_file(path: Path) -> tuple[list[tuple[str, int, bool, bool]], set[str]]:
    """Scan a source file for module-level imports with guard context.

    Returns ((module, dotted, lineno, guarded, type_only), imported_roots) where
    imports nested in functions/classes are skipped (lazy imports) and
    imports inside a module-level `try` or `if` block are guarded.
    """

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return [], set()
    findings: list[tuple[str, int, bool, bool]] = []
    roots: set[str] = set()

    def _walk(
        node: ast.AST,
        *,
        guarded: bool = False,
        type_only: bool = False,
    ) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                if isinstance(child, ast.ImportFrom) and child.level > 0:
                    continue
                module = _strip_import(child)
                if module and module != "typing":
                    dotted = _strip_import_dotted(child)
                    findings.append((module, dotted, child.lineno, guarded, type_only))
                    roots.add(module)
            elif isinstance(child, ast.Try):
                _walk(child, guarded=True, type_only=type_only)
            elif isinstance(child, ast.If):
                type_checking = not type_only and _is_type_checking_guard(child)
                _walk(child, guarded=True, type_only=type_only or type_checking)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            else:
                _walk(child, guarded=guarded, type_only=type_only)

    _walk(tree)
    return findings, roots


def _dist_candidates(module: str, dotted: str | None = None) -> tuple[str, ...]:
    """Map an import to candidate distribution names, dotted path first."""

    if dotted:
        parts = dotted.split(".")
        for index in range(len(parts), 0, -1):
            prefix = ".".join(parts[:index])
            if prefix in ALIASES:
                return ALIASES[prefix]
    if module in ALIASES:
        return ALIASES[module]
    return (_normalize_dep(module),)


def _declared_in_base(finding: ImportFinding, declarations: DependencyDeclarations) -> bool:
    """Return True when the import resolves to a base dependency."""

    return any(
        candidate in declarations.base
        for candidate in _dist_candidates(finding.module, finding.dotted)
    )


def _is_optional(finding: ImportFinding, declarations: DependencyDeclarations) -> bool:
    """Return True when the import resolves to an optional dependency."""

    return any(
        candidate in declarations.optional
        for candidate in _dist_candidates(finding.module, finding.dotted)
    )


def _is_violation(finding: ImportFinding, declarations: DependencyDeclarations) -> bool:
    """Return True when an unguarded import references an undeclared/optional dep."""

    if finding.type_only or finding.guarded:
        return False
    return not _declared_in_base(finding, declarations)


def _status(finding: ImportFinding, declarations: DependencyDeclarations) -> str:
    """Return a classification label for a finding."""

    if _declared_in_base(finding, declarations):
        return "declared"
    if finding.guarded:
        return "guarded"
    if _is_optional(finding, declarations):
        return "optional-unguarded"
    return "undeclared"


def _unused_extras(
    declarations: DependencyDeclarations,
    imported_roots: set[str],
) -> tuple[str, ...]:
    """Return optional distributions with no matching import root in sources."""

    unused: list[str] = []
    for dist in sorted(declarations.optional):
        if _is_dev_tool(dist) or _is_lexigram(dist):
            continue
        candidates = REVERSE_ALIASES.get(dist, ())
        if not candidates:
            candidates = (_normalize_dep(dist),)
        if all(candidate not in imported_roots for candidate in candidates):
            unused.append(dist)
    return tuple(unused)


def _is_dev_tool(dist: str) -> bool:
    """Return True for distribution names used by dev/test/lint tooling only."""

    return dist in {
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "pytest-mock",
        "pytest-xdist",
        "ruff",
        "mypy",
        "black",
        "mkdocs",
        "mkdocs-material",
        "pre-commit",
        "coverage",
        "httpx",
        "respx",
        "freezegun",
        "tox",
        "nox",
        "build",
        "twine",
    }


class OptionalImportsAuditGenerator(MarkdownAuditGenerator):
    """Audit module-level imports of optional or undeclared third-party packages."""

    name = "optional-imports"
    description = (
        "Generate AUDIT_OPTIONAL_IMPORTS.md from module-level import and "
        "pyproject dependency declarations."
    )
    output_file = "AUDIT_OPTIONAL_IMPORTS.md"

    def run(
        self,
        *,
        root: Path | None = None,
        all_mode: bool = False,
    ) -> AuditRunResult:
        """Execute the audit and fail on unguarded optional/undeclared imports."""

        validation = self.validate(root=root)
        if not validation.success:
            return validation
        resolved_root = self.resolve_root(root)
        output_dir = resolved_root if all_mode else resolved_root / "docs/lexigram-docs/audit"
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown, violations = self._render(resolved_root)
        output_path = output_dir / self.output_file
        output_path.write_text(markdown, encoding="utf-8")
        status = "PASS" if violations == 0 else f"{violations} violation(s)"
        return AuditRunResult(
            name=self.name,
            success=violations == 0,
            message=f"{status} -> wrote {output_path.name}",
            output_path=output_path,
        )

    def render_markdown(self, *, root: Path) -> str:
        """Render the optional-imports audit report (protocol compatibility)."""

        return self._render(root)[0]

    def _package_audits(self, root: Path) -> tuple[PackageAudit, ...]:
        """Analyze every package root and return structured results."""

        audits: list[PackageAudit] = []
        for package_dir in self.iter_package_roots(root=root):
            pyproject = package_dir / "pyproject.toml"
            if not pyproject.is_file():
                continue
            sources = package_dir / "src"
            findings: list[ImportFinding] = []
            roots: set[str] = set()
            if sources.is_dir():
                for path in sorted(sources.rglob("*.py")):
                    if any(part == "templates" for part in path.parts):
                        continue
                    for module, dotted, line, guarded, type_only in _scan_file(path)[0]:
                        if _is_stdlib(module) or _is_lexigram(module):
                            continue
                        roots.add(module)
                        findings.append(
                            ImportFinding(
                                module=module,
                                dotted=dotted,
                                file=path.relative_to(package_dir).as_posix(),
                                line=line,
                                guarded=guarded,
                                type_only=type_only,
                            )
                        )
            declarations = _parse_pyproject(pyproject)
            audits.append(
                PackageAudit(
                    name=package_dir.name,
                    declarations=declarations,
                    findings=tuple(findings),
                    unused_extras=_unused_extras(declarations, roots),
                )
            )
        return tuple(audits)

    def _render(self, root: Path) -> tuple[str, int]:
        """Build the report body and count violations."""

        audits = self._package_audits(root)
        lines = [
            "# AUDIT_OPTIONAL_IMPORTS.md",
            "",
            "> Audit of module-level third-party imports against `pyproject.toml`",
            "> dependency declarations. An optional or undeclared third-party",
            "> package imported at module level raises at import time when the",
            "> extra is not installed.",
            ">",
            "> Imports inside `try` blocks, `if TYPE_CHECKING:`, or function and",
            "> class bodies are treated as guarded/lazy imports.",
            "",
            "## Summary",
            "",
            "| Package | Findings | Violations | Unused optional extras |",
            "|---|---|---|---|",
        ]
        for audit in audits:
            lines.append(
                f"| {audit.name} | {len(audit.findings)} | {audit.violations} | "
                f"{len(audit.unused_extras)} |"
            )
        if not audits:
            lines.append("| _no packages_ | 0 | 0 | 0 |")
        lines.append("")

        for audit in audits:
            lines.append(f"## {audit.name}")
            lines.append("")
            if not audit.findings:
                lines.append("No third-party module-level imports.")
                lines.append("")
                continue
            lines.append("| module | status | guard | location |")
            lines.append("|---|---|---|---|")
            for finding in sorted(audit.findings, key=lambda item: (item.file, item.line)):
                guard = (
                    "type-only"
                    if finding.type_only
                    else ("guard" if finding.guarded else "module")
                )
                lines.append(
                    f"| `{finding.module}` | {_status(finding, audit.declarations)} | "
                    f"{guard} | {audit.name}/{finding.file}:{finding.line} |"
                )
            if audit.unused_extras:
                lines.append("")
                lines.append(
                    "Optional extras not imported by package sources: "
                    + ", ".join(f"`{name}`" for name in audit.unused_extras)
                )
            lines.append("")

        return "\n".join(lines), sum(audit.violations for audit in audits)
