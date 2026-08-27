"""Pytest bootstrap for the realtime-monitor demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install. Demo packages are intentionally
excluded from the monorepo aggregate test run (see root ``pyproject.toml``
``norecursedirs``), so these tests are run explicitly:

    uv run pytest demos/realtime-monitor/tests -q
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

_DEMO_ROOT = Path(__file__).resolve().parent

sys.path.insert(0, str(_DEMO_ROOT / "src"))
os.chdir(_DEMO_ROOT)


@pytest.fixture(autouse=True)
def _ensure_cwd() -> None:
    """Pin cwd to the demo root before every test."""
    os.chdir(_DEMO_ROOT)
