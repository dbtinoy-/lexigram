"""Pytest bootstrap for the auth web demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install:

    uv run pytest demos/auth-web/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
