"""Pytest bootstrap for the rag-docs demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install.  Demo packages are intentionally
excluded from the monorepo aggregate test run (see root ``pyproject.toml``
``norecursedirs``), so these tests are run explicitly:

    uv run pytest demos/rag-docs/tests -q
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

_DEMO_ROOT = Path(__file__).resolve().parent

# Lexigram discovers application.yaml from cwd — pin it so tests work
# from any invocation point (repo root or in-demo).
os.chdir(_DEMO_ROOT)
# Add src/ to sys.path so ``from rag_docs...`` resolves in tests.
sys.path.insert(0, str(_DEMO_ROOT / "src"))


@pytest.fixture(autouse=True)
def _ensure_cwd() -> None:
    """Pin cwd to the demo root before every test."""
    os.chdir(_DEMO_ROOT)
