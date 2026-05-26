#!/usr/bin/env python3
"""Reject cross-package use of private names (spec §5.3).

Rules:
1. ``from <pkg>.<sub> import <name>`` where ``name`` starts with "_"
   and the importing module is NOT under the same package (package =
   the first two name parts, e.g. ``lexigram.admin``; private members
   are private to their package, per AGENTS.md). A single-part package
   (``lexigram`` core) owns all its submodules.
2. ``import <pkg>._<something>`` (private module import).
3. Only the project's own packages (``lexigram.*``, ``starter``) are
   policed; stdlib/third-party private imports (e.g.
   ``concurrent.futures.thread``) are out of scope.

Files may carry an explicit exemption comment ``# private-access: allow``.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys


def scan_source(source: str, filename: str = "<string>") -> list[str]:
    """Scan one source file for private-name imports across packages.

    Args:
        source: Python source text.
        filename: Display name used in parse errors.

    Returns:
        Human-readable findings; empty when clean.
    """
    tree = ast.parse(source, filename=filename)
    if "# private-access: allow" in source:
        return []
    importing_pkg = _package_of(filename)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            for alias in node.names:
                if (
                    alias.name.startswith("_")
                    and _is_project_module(node.module)
                    and not _same_package(importing_pkg, _package_of(node.module))
                ):
                    hits.append(f"private import {node.module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if (
                    _is_project_module(alias.name)
                    and not _same_package(importing_pkg, _package_of(alias.name))
                    and any(part.startswith("_") for part in alias.name.split(".")[1:])
                ):
                    hits.append(f"private module import {alias.name}")
    return hits


def _is_project_module(module: str) -> bool:
    return module.split(".", maxsplit=1)[0] in ("lexigram", "starter")


def _package_of(module_or_path: str) -> str:
    """First two parts of a module path/name, e.g. 'lexigram.admin'."""
    parts = module_or_path.replace("/", ".").split(".")
    if "src" in parts:
        last_src = len(parts) - 1 - parts[::-1].index("src")
        parts = parts[last_src + 1 :]
    while parts and parts[-1] in ("py", "__init__"):
        parts.pop()
    return ".".join(parts[:2])


def _same_package(importing: str, imported: str) -> bool:
    """Same-package check; a single-part package owns its submodules."""
    if not importing:
        return False
    if "." not in importing:
        return imported == importing or imported.startswith(importing + ".")
    return imported == importing


def main() -> int:
    """Run the private-access lint over the repo and report findings."""
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    findings: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if "tests" in path.parts or ".venv" in path.parts:
            continue
        rel = path.relative_to(root)
        if not rel.parts[0].startswith("lexigram") and rel.parts[0] != "starter":
            continue
        try:
            source = path.read_text()
        except OSError:
            continue
        try:
            hits = scan_source(source, str(rel))
        except SyntaxError:
            continue
        for hit in hits:
            findings.append(f"{rel}: {hit}")
    if findings:
        print("\n".join(findings))
        return 1
    print("private-access lint: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
