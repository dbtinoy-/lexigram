#!/usr/bin/env python3
"""Proper duplicate API audit for lexigram packages.

Scans Python source files directly (not API.md snapshots) to find true
duplicate definitions, distinguishing:

  INTRA         - same symbol defined in 2+ files within ONE package (bug risk)
  COLLISION     - independently defined in 2+ extension packages (review needed)
  SPECIALIZATION - extension specializes a contracts/core definition (expected)
  CONST_SAME    - same-valued constant in multiple packages (noise)

Only actual definitions are counted (class/function/variable bodies).
Imports like ``from X import Y`` are excluded.

Usage:
  python tools/audit_duplicate_api.py
  python tools/audit_duplicate_api.py --severity INTRA COLLISION
  python tools/audit_duplicate_api.py --include-constants --output report.md
  python tools/audit_duplicate_api.py --min-packages 3
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


# Packages that own the "canonical" definition of a symbol.
# Extensions are expected to specialize (subclass) these, not copy them.
CANONICAL_PACKAGES = frozenset({"lexigram", "lexigram-contracts"})

EXCLUDED_DIRS = frozenset({
    ".venv", "__pycache__", ".git", "node_modules",
    "tests", "test", ".benchmarks", "benchmarks",
    "htmlcov", ".mypy_cache", ".ruff_cache", "dist", "build",
    "example", "examples",
})

SEVERITY_ORDER = ("INTRA", "COLLISION", "SPECIALIZATION", "CONST_SAME")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SymbolDef:
    name: str
    kind: str          # "class" | "function" | "variable"
    package: str
    rel_path: str      # relative to package src root
    lineno: int
    bases: list[str] = field(default_factory=list)
    value_repr: str = ""


@dataclass
class Finding:
    name: str
    severity: str
    occurrences: list[SymbolDef]
    note: str = ""


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    return ""


def _value_repr(node: ast.expr | None) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"...{node.attr}"
    return "..."


def _is_excluded(path: Path, src_root: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.relative_to(src_root).parts)


# ---------------------------------------------------------------------------
# Symbol collection
# ---------------------------------------------------------------------------

def collect_file_symbols(file_path: Path, package: str, rel_path: str) -> list[SymbolDef]:
    """Return top-level definitions (not imports) from a single .py file."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []

    symbols: list[SymbolDef] = []

    for node in tree.body:
        # Skip imports — we only want actual definitions
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue

        if isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            bases = [b for b in (_base_name(b) for b in node.bases) if b]
            symbols.append(SymbolDef(
                name=node.name, kind="class", package=package,
                rel_path=rel_path, lineno=node.lineno, bases=bases,
            ))

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                symbols.append(SymbolDef(
                    name=node.name, kind="function", package=package,
                    rel_path=rel_path, lineno=node.lineno,
                ))

        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and not tgt.id.startswith("_"):
                    symbols.append(SymbolDef(
                        name=tgt.id, kind="variable", package=package,
                        rel_path=rel_path, lineno=node.lineno,
                        value_repr=_value_repr(node.value),
                    ))

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and not node.target.id.startswith("_"):
                symbols.append(SymbolDef(
                    name=node.target.id, kind="variable", package=package,
                    rel_path=rel_path, lineno=node.lineno,
                    value_repr=_value_repr(node.value),
                ))

    return symbols


def find_packages(root: Path) -> list[tuple[str, Path]]:
    """Return (package_name, src_root) for every lexigram-* directory."""
    results = []
    for item in sorted(root.iterdir()):
        if not item.is_dir() or not item.name.startswith("lexigram"):
            continue

        if item.name == "lexigram":
            src = item / "src" / "lexigram"
        else:
            # e.g. lexigram-ai-llm  ->  src/lexigram/ai/llm
            sub = item.name.removeprefix("lexigram-").replace("-", "/")
            src = item / "src" / "lexigram" / sub
            if not src.exists():
                # contracts layout: lexigram-contracts/src/lexigram/contracts
                src = item / "src" / "lexigram"

        if src.exists():
            results.append((item.name, src))

    return results


def collect_all(root: Path) -> dict[str, list[SymbolDef]]:
    """Walk every package and return {symbol_name: [SymbolDef, ...]}."""
    by_name: dict[str, list[SymbolDef]] = defaultdict(list)

    for pkg, src_root in find_packages(root):
        for py_file in sorted(src_root.rglob("*.py")):
            if _is_excluded(py_file, src_root):
                continue
            rel = str(py_file.relative_to(src_root))
            for sym in collect_file_symbols(py_file, pkg, rel):
                by_name[sym.name].append(sym)

    return dict(by_name)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _is_noise_name(name: str) -> bool:
    """Skip single-char TypeVars, all-caps short names, and dunders."""
    if name.startswith("__"):
        return True
    # Short all-uppercase names are almost always TypeVars (T, E, K, V, etc.)
    if len(name) <= 3 and name.isupper():
        return True
    return False


def classify(name: str, all_occs: list[SymbolDef]) -> Finding | None:
    if len(all_occs) < 2 or _is_noise_name(name):
        return None

    # Deduplicate to one representative per (package, kind)
    seen: dict[tuple[str, str], SymbolDef] = {}
    for s in all_occs:
        key = (s.package, s.kind)
        if key not in seen:
            seen[key] = s
    occs = list(seen.values())

    if len(occs) < 2:
        return None

    # Group by package
    by_pkg: dict[str, list[SymbolDef]] = defaultdict(list)
    for s in occs:
        by_pkg[s.package].append(s)

    # ---- INTRA: same name in 2+ files of the same package ----------------
    for pkg, syms in by_pkg.items():
        if len(syms) > 1:
            return Finding(
                name=name, severity="INTRA", occurrences=syms,
                note=f"{len(syms)} definitions within {pkg}",
            )

    # From here each package has exactly one occurrence
    canonical = [s for s in occs if s.package in CANONICAL_PACKAGES]
    extensions = [s for s in occs if s.package not in CANONICAL_PACKAGES]

    # ---- Variables: check if all same value ------------------------------
    if all(s.kind == "variable" for s in occs):
        values = {s.value_repr for s in occs}
        if len(values) == 1:
            return Finding(
                name=name, severity="CONST_SAME", occurrences=occs,
                note=f"Value {next(iter(values))} in {len(occs)} packages",
            )
        return Finding(
            name=name, severity="COLLISION", occurrences=occs,
            note=f"Different values: {sorted(values)}",
        )

    # ---- Classes: specialization vs collision ----------------------------
    if canonical and extensions:
        # Extensions exist alongside a contracts/core definition → SPECIALIZATION
        return Finding(
            name=name, severity="SPECIALIZATION", occurrences=occs,
            note=(
                f"Canonical in {canonical[0].package} ({canonical[0].rel_path}); "
                f"specialized in {', '.join(s.package for s in extensions)}"
            ),
        )

    if len(extensions) >= 2:
        # Two or more unrelated extension packages define the same name
        return Finding(
            name=name, severity="COLLISION", occurrences=occs,
            note=f"No contracts/core version; defined independently in "
                 f"{', '.join(s.package for s in extensions)}",
        )

    # Both lexigram (core) and lexigram-contracts define the same symbol.
    # This violates the hierarchy rule: contracts defines, core consumes.
    if len(canonical) >= 2:
        pkgs = " vs ".join(s.package for s in canonical)
        return Finding(
            name=name, severity="INTRA", occurrences=canonical,
            note=f"Canonical-layer conflict ({pkgs}) — one should own this",
        )

    return None


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

SEVERITY_EMOJI = {
    "INTRA": "🔴",
    "COLLISION": "🟡",
    "SPECIALIZATION": "🟢",
    "CONST_SAME": "⚪",
}

SEVERITY_LABEL = {
    "INTRA": "INTRA-PACKAGE duplicate (bug risk)",
    "COLLISION": "CROSS-EXTENSION collision (review needed)",
    "SPECIALIZATION": "Expected specialization (contracts/core extended)",
    "CONST_SAME": "Shared constant, same value (noise)",
}


def render_markdown(findings: list[Finding], root: Path) -> str:
    from datetime import date

    by_severity: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_severity[f.severity].append(f)

    lines = [
        "# Duplicate API Audit Report",
        "",
        f"Generated: {date.today()}",
        f"Total findings: {len(findings)}",
        "",
    ]

    for sev in SEVERITY_ORDER:
        group = by_severity.get(sev, [])
        if not group:
            continue
        emoji = SEVERITY_EMOJI[sev]
        label = SEVERITY_LABEL[sev]
        lines += [f"## {emoji} {label} ({len(group)})", ""]
        for f in sorted(group, key=lambda x: x.name):
            lines.append(f"### `{f.name}`")
            lines.append(f"_{f.note}_")
            lines.append("")
            for occ in sorted(f.occurrences, key=lambda s: s.package):
                bases = f" → `({', '.join(occ.bases)})`" if occ.bases else ""
                val = f" = `{occ.value_repr}`" if occ.value_repr else ""
                lines.append(f"- **{occ.package}** `{occ.rel_path}:{occ.lineno}` {occ.kind}{bases}{val}")
            lines.append("")

    return "\n".join(lines)


def render_triage_markdown(findings: list[Finding]) -> str:
    from datetime import date

    collision_findings = [f for f in findings if f.severity == "COLLISION"]

    # Category buckets: (label, predicate)
    categories: list[tuple[str, object]] = [
        ("CONSTANTS", lambda n: n.isupper()),
        ("CONFIG", lambda n: n.endswith(("Config", "Settings", "Options"))),
        ("ERROR", lambda n: n.endswith(("Error", "Exception"))),
        ("PROTOCOL", lambda n: n.endswith("Protocol")),
        ("TYPE_ENUM", lambda n: n.endswith(("Type", "Mode", "Status", "State"))),
    ]

    def categorize(name: str) -> str:
        for label, pred in categories:  # type: ignore[assignment]
            if pred(name):  # type: ignore[operator]
                return label
        return "OTHER"

    grouped: dict[str, list[Finding]] = defaultdict(list)
    for f in collision_findings:
        grouped[categorize(f.name)].append(f)

    cat_order = [c for c, _ in categories] + ["OTHER"]

    lines = [
        "# Collision Triage Report",
        "",
        f"Generated: {date.today()}",
        f"Total COLLISION findings: {len(collision_findings)}",
        "",
        "Grouped by pattern category to aid allowlist review.",
        "",
    ]

    for cat in cat_order:
        group = grouped.get(cat, [])
        if not group:
            continue
        lines += [f"## {cat} ({len(group)})", ""]
        for f in sorted(group, key=lambda x: x.name):
            pkgs = ", ".join(sorted({s.package for s in f.occurrences}))
            lines.append(f"### `{f.name}`")
            lines.append(f"_Packages: {pkgs}_")
            lines.append("")
            for occ in sorted(f.occurrences, key=lambda s: s.package):
                bases = f" → `({', '.join(occ.bases)})`" if occ.bases else ""
                val = f" = `{occ.value_repr}`" if occ.value_repr else ""
                lines.append(f"- **{occ.package}** `{occ.rel_path}:{occ.lineno}` {occ.kind}{bases}{val}")
            lines.append("")

    return "\n".join(lines)


def render_summary(findings: list[Finding]) -> str:
    by_sev: dict[str, int] = defaultdict(int)
    for f in findings:
        by_sev[f.severity] += 1

    lines = ["", "=== Audit Summary ==="]
    for sev in SEVERITY_ORDER:
        count = by_sev.get(sev, 0)
        emoji = SEVERITY_EMOJI[sev]
        label = SEVERITY_LABEL[sev]
        lines.append(f"  {emoji} {sev:20s} {count:4d}  ({label})")
    lines.append(f"  {'TOTAL':20s} {len(findings):4d}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Enum compliance check (--check-enums)
# ---------------------------------------------------------------------------

@dataclass
class EnumViolation:
    name: str
    package: str
    rel_path: str
    lineno: int
    bases: list[str]


def check_enum_compliance(root: Path) -> list[EnumViolation]:
    """Find classes that inherit from Enum without str or int as a co-base.

    AGENTS.md rule: string enums use (str, Enum); ordering enums use (int, Enum).
    Plain (Enum) without a type mixin is never correct in production source.
    """
    violations: list[EnumViolation] = []
    for pkg, src_root in find_packages(root):
        for py_file in sorted(src_root.rglob("*.py")):
            if _is_excluded(py_file, src_root):
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (OSError, UnicodeDecodeError, SyntaxError):
                continue
            for node in tree.body:
                if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
                    continue
                bases = [_base_name(b) for b in node.bases]
                if "Enum" not in bases and "IntEnum" not in bases:
                    continue
                # Passes: has str/int co-base, or is IntEnum (acceptable for ordering)
                has_str = "str" in bases or "StrEnum" in bases
                has_int = "int" in bases or "IntEnum" in bases
                if has_str or has_int:
                    continue
                violations.append(EnumViolation(
                    name=node.name,
                    package=pkg,
                    rel_path=str(py_file.relative_to(src_root)),
                    lineno=node.lineno,
                    bases=[b for b in bases if b],
                ))
    return violations


def render_enum_violations(violations: list[EnumViolation]) -> str:
    from datetime import date

    lines = [
        "# Enum Compliance Report",
        "",
        f"Generated: {date.today()}",
        f"Violations: {len(violations)}",
        "",
        "All production Enum classes must use `(str, Enum)` for string enums",
        "or `(int, Enum)` / `IntEnum` for ordering enums. Plain `(Enum)` is never correct.",
        "",
    ]
    for v in sorted(violations, key=lambda x: (x.package, x.rel_path, x.name)):
        lines.append(f"- **{v.package}** `{v.rel_path}:{v.lineno}` — `class {v.name}({', '.join(v.bases)})`")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--severity", nargs="+", choices=SEVERITY_ORDER, default=list(SEVERITY_ORDER),
        metavar="SEV", help="Severities to include (default: all)",
    )
    parser.add_argument(
        "--output", "-o", metavar="FILE",
        help="Write markdown report to FILE (default: print to stdout)",
    )
    parser.add_argument(
        "--min-packages", type=int, default=2, metavar="N",
        help="Only report symbols found in at least N packages (default: 2)",
    )
    parser.add_argument(
        "--exclude-constants", action="store_true",
        help="Hide CONST_SAME findings (reduces noise)",
    )
    parser.add_argument(
        "--allowlist", metavar="FILE",
        help="File with accepted collision symbol names (one per line, # for comments)",
    )
    parser.add_argument(
        "--triage", action="store_true",
        help="Output COLLISION findings grouped by pattern category (for allowlist review)",
    )
    parser.add_argument(
        "--check-enums", action="store_true",
        help="Check for Enum classes missing str/int co-base (AGENTS.md rule)",
    )
    args = parser.parse_args()

    root = Path(__file__).parent.parent

    if args.check_enums:
        print("Checking enum compliance...", file=sys.stderr)
        violations = check_enum_compliance(root)
        print(f"  {len(violations)} violation(s)", file=sys.stderr)
        report = render_enum_violations(violations)
        if args.output:
            Path(args.output).write_text(report, encoding="utf-8")
            print(f"\nReport written to: {args.output}", file=sys.stderr)
        else:
            print(report)
        sys.exit(1 if violations else 0)

    print("Scanning packages...", file=sys.stderr)
    by_name = collect_all(root)
    print(f"  {len(by_name)} unique symbol names across all packages", file=sys.stderr)

    findings: list[Finding] = []
    for name, occs in by_name.items():
        f = classify(name, occs)
        if f is None:
            continue
        if f.severity not in args.severity:
            continue
        if args.exclude_constants and f.severity == "CONST_SAME":
            continue
        pkg_count = len({s.package for s in f.occurrences})
        if pkg_count < args.min_packages:
            continue
        findings.append(f)

    # Apply allowlist: suppress accepted collision names
    allowed: set[str] = set()
    if args.allowlist:
        try:
            text = Path(args.allowlist).read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"error: allowlist file not found: {args.allowlist}", file=sys.stderr)
            sys.exit(1)
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                allowed.add(line)
        findings = [f for f in findings if f.name not in allowed]

    print(f"  {len(findings)} findings after filtering", file=sys.stderr)
    print(render_summary(findings), file=sys.stderr)

    if args.triage:
        report = render_triage_markdown(findings)
    else:
        report = render_markdown(findings, root)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"\nReport written to: {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
