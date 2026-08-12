from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from scripts.core.package_inventory import discover_package_paths
from scripts.core.rules_catalog import (
    SEVERITY_ORDER,
    RuleCatalogContext,
    RuleDefinition,
    RuleFinding,
    RuleSeverity,
    RuleSourceFile,
    build_rules_catalog,
    make_rule_finding,
)
from scripts.core.validation import PackageCoverageResult, validate_package_coverage


@dataclass(frozen=True, slots=True)
class RuleScanResult:
    """Structured output from a full Lexigram rules scan."""

    findings: tuple[RuleFinding, ...]
    coverage: PackageCoverageResult


def run_rules(root: Path | str, packages: tuple[str, ...] | None = None) -> RuleScanResult:
    """Run the configured Lexigram rules against every discovered package source tree."""

    root_path = Path(root).resolve()
    if packages is None:
        package_paths = discover_package_paths(root_path)
    else:
        try:
            member_paths = discover_package_paths(root_path)
        except FileNotFoundError:
            member_paths = ()
        named = {path.name: path for path in member_paths}
        package_paths = tuple(named[p] if p in named else Path(p) for p in packages)
    source_files, syntax_findings = _load_source_files(root=root_path, package_paths=package_paths)
    covered_packages = tuple(sorted({source_file.package_name for source_file in source_files}))
    coverage = validate_package_coverage(
        tuple(p.name for p in package_paths), covered_packages
    )
    context = RuleCatalogContext(
        root=root_path,
        module_owners=_build_module_owner_map(source_files),
    )
    findings = tuple(
        sorted(
            (
                *syntax_findings,
                *_run_catalog(source_files=source_files, context=context, catalog=build_rules_catalog()),
            ),
            key=_finding_sort_key,
        )
    )
    return RuleScanResult(findings=findings, coverage=coverage)


def _run_catalog(
    *,
    source_files: tuple[RuleSourceFile, ...],
    context: RuleCatalogContext,
    catalog: tuple[RuleDefinition, ...],
) -> tuple[RuleFinding, ...]:
    """Apply every rule in the catalog to every discovered source file."""

    findings: list[RuleFinding] = []
    for source_file in source_files:
        for rule in catalog:
            findings.extend(rule.detector(source_file, context))
    return tuple(sorted(findings, key=_finding_sort_key))


def _load_source_files(
    *,
    root: Path,
    package_paths: tuple[Path, ...],
) -> tuple[tuple[RuleSourceFile, ...], tuple[RuleFinding, ...]]:
    """Load Python source files from package src trees and capture syntax failures."""

    loaded_files: list[RuleSourceFile] = []
    syntax_findings: list[RuleFinding] = []
    for package_rel in package_paths:
        package_root = root / package_rel
        package_name = package_rel.name
        source_root = package_root / "src"
        if not source_root.is_dir():
            continue
        for path in sorted(source_root.rglob("*.py")):
            if "__pycache__" in path.parts or "templates" in path.parts:
                continue
            relative_path = path.relative_to(root)
            source_text = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source_text, filename=str(relative_path))
            except SyntaxError as exc:
                syntax_findings.append(
                    make_rule_finding(
                        rule_id="python-syntax-error",
                        severity=RuleSeverity.IMPORTANT,
                        owner="framework",
                        rationale="Files with Python syntax errors cannot be reliably scanned and must be fixed before audit results are trustworthy.",
                        package_name=package_name,
                        path=relative_path,
                        line=max(1, exc.lineno or 1),
                        message=(
                            f"{relative_path.as_posix()} failed to parse with SyntaxError: "
                            f"{exc.msg or 'invalid syntax'}."
                        ),
                    )
                )
                continue
            loaded_files.append(
                RuleSourceFile(
                    package_name=package_name,
                    package_root=package_root,
                    path=path,
                    relative_path=relative_path,
                    module_name=_module_name_from_path(path.relative_to(source_root)),
                    tree=tree,
                )
            )
    return tuple(loaded_files), tuple(syntax_findings)


def _module_name_from_path(relative_path: Path) -> str:
    """Convert a source-root-relative file path into its Python module name."""

    parts = list(relative_path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _build_module_owner_map(source_files: tuple[RuleSourceFile, ...]) -> dict[str, frozenset[str]]:
    """Build a longest-prefix lookup from module path to owning package."""

    module_owners: dict[str, set[str]] = {}
    for source_file in source_files:
        if not source_file.module_name:
            continue
        module_owners.setdefault(source_file.module_name, set()).add(source_file.package_name)
    return {
        module_name: frozenset(sorted(owners))
        for module_name, owners in module_owners.items()
    }


def _finding_sort_key(finding: RuleFinding) -> tuple[int, str, int, str]:
    """Return the deterministic sort key for rule findings."""

    return (
        SEVERITY_ORDER[finding.severity],
        finding.path.as_posix(),
        finding.line,
        finding.rule_id,
    )


__all__ = [
    "RuleFinding",
    "RuleScanResult",
    "RuleSeverity",
    "run_rules",
]
