"""Pytest bootstrap for the resilient rates demo.

Two jobs:

1. Make imports and config discovery work regardless of *where* pytest is
   invoked: chdir into this demo's root (where ``application.yaml`` lives)
   and put ``src`` on ``sys.path``. The framework auto-discovers
   ``application.yaml`` from the working directory, so after this chdir no
   custom configuration loader is needed anywhere.
2. Boot the real composition root for tests via fixtures.

    uv run pytest demos/resilient-rates/tests -q        # from repo root works too
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import os
import sys

import httpx
import pytest
from starlette.applications import Starlette

_DEMO_ROOT = Path(__file__).resolve().parent.parent

# Lexigram discovers application.yaml from cwd — pin it so tests work
# from any invocation point (repo root or in-demo).
os.chdir(_DEMO_ROOT)
# Add src/ to sys.path so ``from rates...`` resolves in tests.
sys.path.insert(0, str(_DEMO_ROOT / "src"))


@pytest.fixture(autouse=True)
def _ensure_cwd() -> None:
    """Pin CWD to demo root for every test (framework reads application.yaml from cwd)."""
    os.chdir(_DEMO_ROOT)
