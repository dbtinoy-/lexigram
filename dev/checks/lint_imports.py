#!/usr/bin/env python3
"""Namespace-aware import-linter wrapper for the Lexigram monorepo.

Background
----------
Standard import-linter / grimp cannot traverse ``pkgutil.extend_path``
namespace packages.  grimp's ``ImportLibPackageFinder`` resolves a
package through ``importlib.util.find_spec`` and treats any package
with a non-namespace parent as a plain top-level module, so extension
packages (``lexigram.contracts``, ``lexigram.cache``, ``lexigram.web``,
etc.) that live in their own ``lexigram-*/src/lexigram`` directories
are either missed or rejected as ``NotATopLevelModule``.

Fix
----
Before grimp's finder runs, this script:

1. Imports the root ``lexigram`` package so that ``pkgutil.extend_path``
   populates ``lexigram.__path__`` with **all** installed namespace
   directories (one per editable-installed sub-package).

2. Builds a temporary merged view of the entire namespace as a single
   directory tree (symlinks from every namespace directory, merged by
   name).  The view mirrors the runtime layout:
   ``lexigram/contracts/...``, ``lexigram/ai/governance/...``, etc.

3. Patches ``ImportLibPackageFinder.determine_package_directories``
   (grimp >= 3.13 returns a *set* of directories) to return the view
   for ``lexigram`` and ``lexigram.*``.  Other packages use the
   original ``find_spec`` logic unchanged.

grimp walks the view with ``os.walk(followlinks=True)``, so the
symlinked tree is fully visible to it. This gives grimp a complete
module view of the ``lexigram.*`` namespace so every contract in
``.importlinter`` can be evaluated correctly.

Usage
-----
    uv run python dev/checks/lint_imports.py            # full check
    uv run python dev/checks/lint_imports.py --verbose  # verbose output

Any flags accepted by the ``lint-imports`` CLI can be passed through.
"""
from __future__ import annotations

import atexit
import os
import shutil
import sys
import tempfile

# ── 1. Bootstrap: import root namespace to trigger pkgutil.extend_path ─────────
# Importing the root package runs pkgutil.extend_path and expands
# lexigram.__path__ with every editable-installed sub-package src dir.
import lexigram  # noqa: F401


def _build_view() -> str:
    """Merge every lexigram namespace directory into one temp tree.

    The view mirrors the runtime layout: real directories for every
    package level, one symlink per module file.  Real directories mean
    grimp's directory walk (with ``followlinks=True``) descends into
    unioned packages correctly and no write ever touches the real
    repository tree.

    Returns:
        The path of the merged view directory.
    """
    view = tempfile.mkdtemp(prefix="lexigram-lint-view-")
    atexit.register(shutil.rmtree, view, ignore_errors=True)

    # Skip the workspace root (detected by its pyproject.toml): it only
    # holds repo tooling, benchmarks, and docs, not namespace modules.
    for path in lexigram.__path__:
        if os.path.exists(os.path.join(path, "pyproject.toml")):
            continue
        for dirpath, dirnames, filenames in os.walk(path):
            rel = os.path.relpath(dirpath, path)
            target = view if rel == "." else os.path.join(view, rel)
            if rel != ".":
                os.makedirs(target, exist_ok=True)
            dirnames[:] = [
                d for d in dirnames if not d.startswith(".") and d != "__pycache__"
            ]
            for filename in filenames:
                if filename.startswith(".") or filename.endswith(".pyc"):
                    continue
                dst = os.path.join(target, filename)
                if not os.path.exists(dst):
                    os.symlink(os.path.join(dirpath, filename), dst)
    return view


# Profile: run only once per process.
_VIEW_ROOT = _build_view()

# ── 2. Monkey-patch grimp's PackageFinder ───────────────────────────────────────
from grimp.adaptors.packagefinder import ImportLibPackageFinder as _Finder  # noqa: E402

_original_determine = _Finder.determine_package_directories


def _namespace_aware_determine(
    self: _Finder, package_name: str, file_system: object
) -> set[str]:
    """Return the merged view directory for any ``lexigram.*`` package.

    grimp >= 3.13 resolves packages through ``determine_package_directories``
    (plural), which returns a *set* of physical directories.  For the
    ``lexigram`` namespace we return the single merged view directory so
    sub-packages spread across many physical ``lexigram-*/src`` trees
    resolve as one tree; any other name uses the original
    ``importlib.util.find_spec`` resolution.

    Args:
        package_name: Name of the package grimp is resolving.
        file_system: The grimp filesystem adaptor (unused here).

    Returns:
        For any ``lexigram.*`` module the matching directory inside the
        merged view; for other names the original finder's result.
    """
    if package_name == "lexigram" or package_name.startswith("lexigram."):
        parts = package_name.split(".")
        view_dir = _VIEW_ROOT
        for part in parts[1:]:
            view_dir = os.path.join(view_dir, part)
        if os.path.isdir(view_dir):
            return {view_dir}
    return _original_determine(  # type: ignore[return-value]
        self, package_name=package_name, file_system=file_system
    )


_Finder.determine_package_directories = _namespace_aware_determine  # type: ignore[method-assign]

# ── 3. Hand off to import-linter's standard CLI ─────────────────────────────────
# lint_imports_command is a Click command; calling it with no arguments
# reads the project configuration and runs the configured semantics.
from importlinter.cli import lint_imports_command  # noqa: E402

if __name__ == "__main__":
    sys.exit(lint_imports_command())
