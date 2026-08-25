"""Canonical repo-root resolution and import bootstrap for dev/ scripts.

Standalone guard scripts (``dev/check_*.py``) are executed as plain files
by CI and the Makefile, so ``dev`` is not importable until it is put on
``sys.path``.  Every script previously carried its own copy of that shim;
they now share this one.
"""

from __future__ import annotations

from pathlib import Path
import sys

# dev/core/bootstrap.py → parents[0]=core, [1]=dev, [2]=repo root
REPO_ROOT = Path(__file__).resolve().parents[2]


def ensure_dev_importable() -> Path:
    """Make ``import dev.*`` work when run as a standalone file.

    Idempotent; returns the resolved repository root so callers can derive
    paths from one canonical constant.
    """
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return REPO_ROOT
