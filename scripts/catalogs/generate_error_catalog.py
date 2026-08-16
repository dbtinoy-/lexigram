#!/usr/bin/env python3
"""
Generate REF_ERROR_CODES.md — authoritative error code registry.

Scans all `src/` trees for `_code = "LEX_ERR_*"` assignments and
produces a structured Markdown registry.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.core.package_inventory import discover_package_paths

REPO_ROOT = Path.cwd()
SRC_GLOB = "*/src/**/*.py"
LEX_ERR_RE = re.compile(r'LEX_ERR_([A-Z0-9_]+)_(\d{3})')

EXCLUDED_DIRS = {"__pycache__", ".egg-info", ".git", "node_modules", ".mypy_cache", ".ruff_cache", ".pytest_cache", "templates"}
EXCLUDED_FILES = set()  # Scan all files including __init__.py

# Patterns that identify exception-like classes
EXCEPTION_SUFFIXES = ("Error", "Exception")
EXCEPTION_BASES = {"Exception", "BaseException", "ValueError", "TypeError", "KeyError", "RuntimeError",
                   "LookupError", "OSError", "IOError", "ImportError", "StopIteration", "AttributeError",
                   "Warning", "UserWarning"}


def is_exception_class(class_name: str, parents: list[str]) -> bool:
    """Check if a class looks like an exception type."""
    if class_name.endswith(EXCEPTION_SUFFIXES):
        return True
    if any(p.endswith(EXCEPTION_SUFFIXES) or p in EXCEPTION_BASES for p in parents):
        return True
    return False


def discover_packages(include_all: bool = False) -> list[Path]:
    """Discover src trees of all workspace member packages at repo root."""
    packages: list[Path] = []
    for rel in discover_package_paths(REPO_ROOT):
        src_dir = REPO_ROOT / rel / "src"
        if src_dir.exists():
            packages.append(src_dir)
    return packages


class CodeVisitor(ast.NodeVisitor):
    """Find _code assignments and their enclosing classes."""

    def __init__(self, filepath: str, package: str) -> None:
        self.filepath = filepath
        self.package = package
        self.entries: list[dict] = []  # List of dicts with code, class_name, parents
        self._current_class: str | None = None
        self._current_parents: list[str] = []
        self._current_docstring: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        old_class = self._current_class
        old_parents = self._current_parents
        self._current_class = node.name
        self._current_parents = [
            _get_name(base) for base in node.bases
        ]
        self._current_docstring = ast.get_docstring(node)

        # Visit child nodes (including _code assignments)
        self.generic_visit(node)

        self._current_class = old_class
        self._current_parents = old_parents
        self._current_docstring = None

    def _record_code(self, code_value: ast.AST) -> None:
        """Record a _code assignment if it matches LEX_ERR_* pattern."""
        if isinstance(code_value, ast.Constant) and isinstance(code_value.value, str):
            code = code_value.value
        elif isinstance(code_value, ast.Name):
            # Handle references like _code = SOME_VARIABLE
            code = code_value.id  # We'll check later if this resolves
            return  # Skip non-literal code refs for now
        else:
            return
        m = LEX_ERR_RE.match(code)
        if m:
            doc = (self._current_docstring or "").strip()
            self.entries.append({
                "code": code,
                "domain": m.group(1),
                "class_name": self._current_class or "(module-level)",
                "parents": list(self._current_parents) if self._current_class else [],
                "docstring": doc,
                "file": self.filepath,
                "package": self.package,
            })

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_code":
                self._record_code(node.value)
                break

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.target.id == "_code" and node.value:
            self._record_code(node.value)


class NoCodeVisitor(ast.NodeVisitor):
    """Find exception classes without a _code attribute."""

    def __init__(self, filepath: str, package: str, known_coded_classes: set[str]) -> None:
        self.filepath = filepath
        self.package = package
        self.known_coded_classes = known_coded_classes  # Class names that already have LEX_ERR_ codes
        self.entries: list[dict] = []
        self._has_code = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        parents = [_get_name(base) for base in node.bases]
        if not is_exception_class(node.name, parents):
            return

        # Check if this class has a _code assignment
        self._has_code = False
        self.generic_visit(node)

        if not self._has_code and node.name not in self.known_coded_classes:
            self.entries.append({
                "class_name": node.name,
                "parents": parents,
                "file": self.filepath,
                "package": self.package,
            })

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_code":
                self._has_code = True
                return

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.target.id == "_code":
            self._has_code = True


def _get_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Subscript):
        return f"{_get_name(node.value)}[{_get_name(node.slice)}]"
    if isinstance(node, ast.Tuple):
        return ", ".join(_get_name(e) for e in node.elts)
    return "?"  # Fallback


def scan_package(src_dir: Path) -> list[dict]:
    """Scan a single package for error codes."""
    entries = []
    package_name = src_dir.parent.name

    for pyfile in src_dir.rglob("*.py"):
        # Skip __init__.py
        if pyfile.name in EXCLUDED_FILES:
            continue
        # Check exclusions
        if any(part in EXCLUDED_DIRS for part in pyfile.parts):
            continue
        rel_path = pyfile.relative_to(REPO_ROOT)
        try:
            source = pyfile.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(pyfile))
            visitor = CodeVisitor(str(rel_path), package_name)
            visitor.visit(tree)
            entries.extend(visitor.entries)
        except SyntaxError:
            print(f"  [warn] Syntax error in {rel_path}, skipping")
        except Exception as e:
            print(f"  [warn] Error parsing {rel_path}: {e}, skipping")

    return entries


def scan_no_code_classes(src_dir: Path, known_coded_classes: set[str]) -> list[dict]:
    """Scan a single package for exception-like classes without _code."""
    entries = []
    package_name = src_dir.parent.name

    for pyfile in src_dir.rglob("*.py"):
        if pyfile.name in EXCLUDED_FILES:
            continue
        if any(part in EXCLUDED_DIRS for part in pyfile.parts):
            continue
        rel_path = pyfile.relative_to(REPO_ROOT)
        try:
            source = pyfile.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(pyfile))
            visitor = NoCodeVisitor(str(rel_path), package_name, known_coded_classes)
            visitor.visit(tree)
            entries.extend(visitor.entries)
        except SyntaxError:
            pass  # Silent for no-code scan
        except Exception:
            pass

    return entries


def build_domain_summary(entries: list[dict]) -> dict[str, dict]:
    """Build domain summary — count, gaps, packages."""
    domains: dict[str, set[str]] = defaultdict(set)
    domain_codes: dict[str, list[str]] = defaultdict(list)
    domain_packages: dict[str, set[str]] = defaultdict(set)

    for e in entries:
        domain = e["domain"]
        domain_codes[domain].append(e["code"])
        domain_packages[domain].add(e["package"])

    summary = {}
    for domain in sorted(domain_codes.keys()):
        codes = sorted(domain_codes[domain])
        count = len(codes)
        # Check gaps
        nums = set()
        for c in codes:
            m = LEX_ERR_RE.match(c)
            if m:
                nums.add(int(m.group(2)))
        max_num = max(nums) if nums else 0
        expected = set(range(1, max_num + 1))
        gaps = expected - nums
        gap_str = ", ".join(f"{n:03d}" for n in sorted(gaps)) if gaps else "—"
        pkgs = sorted(domain_packages[domain])
        summary[domain] = {
            "count": count,
            "gaps": gap_str,
            "packages": pkgs,
        }
    return summary


def package_sort_key(pkg: str) -> tuple:
    """Sort packages: contracts first, then lexigram, then extensions alphabetically."""
    if pkg == "lexigram-contracts":
        return (0, "")
    if pkg == "lexigram":
        return (1, "")
    return (2, pkg)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate REF_ERROR_CODES.md")
    parser.add_argument("--all", action="store_true", help="Write generated docs to repo root (publish mode)")
    args = parser.parse_args()

    all_entries: list[dict] = []
    packages = discover_packages(include_all=args.all)
    for src_dir in packages:
        pkg_name = src_dir.parent.name
        entries = scan_package(src_dir)
        all_entries.extend(entries)

    # Deduplicate by code
    seen_codes: set[str] = set()
    unique_entries: list[dict] = []
    for e in all_entries:
        if e["code"] not in seen_codes:
            seen_codes.add(e["code"])
            unique_entries.append(e)

    total_codes = len(unique_entries)

    # Group by package
    package_entries: dict[str, list[dict]] = defaultdict(list)
    for e in unique_entries:
        package_entries[e["package"]].append(e)

    # Sort entries within each package
    for pkg in package_entries:
        package_entries[pkg].sort(key=lambda x: x["code"])

    # Collect all class names that already have codes (for no-code exclusion)
    coded_class_names: set[str] = set()
    for e in unique_entries:
        coded_class_names.add(e["class_name"])

    # Scan for exception classes WITHOUT _code
    all_no_code: list[dict] = []
    for src_dir in packages:
        no_code = scan_no_code_classes(src_dir, coded_class_names)
        all_no_code.extend(no_code)

    # Deduplicate no-code entries by (class_name, package)
    seen_nc: set[tuple[str, str]] = set()
    unique_no_code: list[dict] = []
    for e in all_no_code:
        key = (e["class_name"], e["package"])
        if key not in seen_nc:
            seen_nc.add(key)
            unique_no_code.append(e)

    # Group no-code by package
    no_code_by_pkg: dict[str, list[dict]] = defaultdict(list)
    for e in unique_no_code:
        no_code_by_pkg[e["package"]].append(e)
    for pkg in no_code_by_pkg:
        no_code_by_pkg[pkg].sort(key=lambda x: x["class_name"])

    domain_summary = build_domain_summary(unique_entries)

    # --- Generate markdown ---
    lines: list[str] = []
    lines.append("# REF_ERROR_CODES.md — Lexigram Framework Error Code Registry")
    lines.append("")
    lines.append(f"**Date:** {datetime.now(UTC).strftime('%Y-%m-%d')}")
    lines.append(f"**Total registered codes:** {total_codes}")
    lines.append(f"**Total domains:** {len(domain_summary)}")
    lines.append(f"**Total packages contributing codes:** {len(package_entries)}")
    lines.append("")
    lines.append("> This is the **authoritative registry** of all `LEX_ERR_*` error codes in the")
    lines.append("> Lexigram Framework monorepo. Every exception class carrying a `_code` attribute")
    lines.append("> is listed here. Generated by scanning all `*.py` source files (excluding tests")
    lines.append("> and examples) for `_code` assignments matching `LEX_ERR_<DOMAIN>_<NNN>`.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Domain Summary")
    lines.append("")
    lines.append("| Domain Tag | Count | Gaps | Package(s) |")
    lines.append("|:-----------|------:|:-----|:-----------|")
    for domain in sorted(domain_summary.keys()):
        s = domain_summary[domain]
        lines.append(f"| `{domain}` | {s['count']} | {s['gaps']} | {', '.join(s['packages'])} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Full Registry (by Package)")
    lines.append("")
    sorted_packages = sorted(package_entries.keys(), key=package_sort_key)
    for pkg in sorted_packages:
        entries = package_entries[pkg]
        lines.append(f"### `{pkg}` ({len(entries)} codes)")
        lines.append("")
        lines.append("| Code | Class | Description | File | Inherits From |")
        lines.append("|:-----|:------|:------------|:-----|:--------------|")
        for e in entries:
            parents_str = ", ".join(e["parents"]) if e["parents"] else "—"
            desc = e.get("docstring", "") or ""
            # Flatten multi-line docstrings into single lines
            desc = desc.replace("\n", " ").replace("\r", " ").strip()
            # Collapse repeated whitespace from flattened newlines
            desc = " ".join(desc.split())
            # Truncate long descriptions
            if len(desc) > 100:
                desc = desc[:97] + "..."
            desc = desc or "—"
            lines.append(f"| `{e['code']}` | `{e['class_name']}` | {desc} | `{e['file']}` | {parents_str} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 3. Code Gaps by Domain")
    lines.append("")
    total_gaps = 0
    for domain in sorted(domain_summary.keys()):
        s = domain_summary[domain]
        if s["gaps"] != "—":
            total_gaps += 1
    if total_gaps == 0:
        lines.append("*No gaps detected — all sequences are contiguous.*")
    else:
        for domain in sorted(domain_summary.keys()):
            s = domain_summary[domain]
            if s["gaps"] != "—":
                lines.append(f"- **{domain}**: missing codes {s['gaps']}")
    lines.append("")

    lines.append("## 4. Exception Classes Without `_code`")
    lines.append("")
    lines.append("These exception classes were found in `src/` trees but their containing")
    lines.append("file has **no `_code` assignment**. They are candidates for registration.")
    lines.append("")
    lines.append(f"**Total:** {len(unique_no_code)} classes across {len(no_code_by_pkg)} packages")
    lines.append("")
    sorted_no_code_pkgs = sorted(no_code_by_pkg.keys(), key=package_sort_key)
    for pkg in sorted_no_code_pkgs:
        entries = no_code_by_pkg[pkg]
        lines.append(f"### `{pkg}` ({len(entries)} classes)")
        lines.append("")
        lines.append("| Class | Inherits From | File |")
        lines.append("|:------|:--------------|:-----|")
        for e in entries:
            parents_str = ", ".join(e["parents"]) if e["parents"] else "—"
            lines.append(f"| `{e['class_name']}` | {parents_str} | `{e['file']}` |")
        lines.append("")
    lines.append("")

    lines.append("## 5. Duplicate Codes")
    lines.append("")
    code_counts = defaultdict(list)
    for e in all_entries:
        code_counts[e["code"]].append(e)
    dupes = {k: v for k, v in code_counts.items() if len(v) > 1}
    if not dupes:
        lines.append("✅ **No duplicate codes detected.** Every `LEX_ERR_*` code is unique.")
    else:
        lines.append("⚠️ **Duplicate codes found:**")
        for code, occurrences in sorted(dupes.items()):
            lines.append(f"- `{code}` appears {len(occurrences)} times:")
            for occ in occurrences:
                lines.append(f"  - `{occ['class_name']}` in `{occ['file']}`")
    lines.append("")

    # --- Packages without codes ---
    all_pkg_names: set[str] = set()
    for src_dir in packages:
        all_pkg_names.add(src_dir.parent.name)
    pkg_with_codes = set(package_entries.keys())
    pkg_without_codes = sorted(all_pkg_names - pkg_with_codes)
    if pkg_without_codes:
        lines.append("## 6. Packages Without Registered Codes")
        lines.append("")
        lines.append("These packages have source files but **no `LEX_ERR_*` codes** registered.")
        lines.append("")
        lines.append(f"**Total:** {len(pkg_without_codes)} packages")
        lines.append("")
        for pkg in pkg_without_codes:
            lines.append(f"- `{pkg}`")
        lines.append("")

    # --- Suspicious exception classes ---
    suspicious_names = {"WidgetNotFoundError", "TemplateNotFoundError", "PlaceholderError", "MockError", "FakeError"}
    suspicious = [e for e in unique_no_code if e["class_name"] in suspicious_names]
    if suspicious:
        lines.append("## 7. Suspicious Exception Classes (Potential Leftovers)")
        lines.append("")
        lines.append("These classes have names suggestive of template/placeholder code and")
        lines.append("may be leftover scaffolding that was never cleaned up.")
        lines.append("")
        lines.append("| Class | File | Package |")
        lines.append("|:------|:-----|:--------|")
        for e in suspicious:
            lines.append(f"| `{e['class_name']}` | `{e['file']}` | `{e['package']}` |")
        lines.append("")

    lines.append("## 8. Full Index by Domain")
    lines.append("")
    lines.append("Complete alphabetical listing of all codes grouped by domain tag.")
    lines.append("")
    # Group by domain
    domain_index: dict[str, list[dict]] = defaultdict(list)
    for e in unique_entries:
        domain_index[e["domain"]].append(e)
    for domain in sorted(domain_index.keys()):
        entries = domain_index[domain]
        lines.append(f"### `{domain}` ({len(entries)} codes)")
        lines.append("")
        lines.append("| Code | Class | Description | Package |")
        lines.append("|:-----|:------|:------------|:--------|")
        for e in sorted(entries, key=lambda x: x["code"]):
            desc = e.get("docstring", "") or ""
            desc = desc.replace("\n", " ").replace("\r", " ").strip()
            desc = " ".join(desc.split())
            if len(desc) > 80:
                desc = desc[:77] + "..."
            desc = desc or "—"
            lines.append(f"| `{e['code']}` | `{e['class_name']}` | {desc} | `{e['package']}` |")
        lines.append("")

    refs_dir = REPO_ROOT / "docs/lexigram-docs/reference" if not args.all else REPO_ROOT
    refs_dir.mkdir(parents=True, exist_ok=True)
    output_path = refs_dir / "REF_ERROR_CODES.md"
    output_path.write_text("\n".join(lines) + "\n")
    print(f"✅ Generated {output_path} — {total_codes} codes across {len(package_entries)} packages")


if __name__ == "__main__":
    main()
