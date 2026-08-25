"""Pytest bootstrap for the resilient rates demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install. Demo packages are intentionally
excluded from the monorepo aggregate test run (see root ``pyproject.toml``
``norecursedirs``), so these tests are run explicitly:

    uv run pytest demos/resilient-rates/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# Auto-discovery of application.yaml requires the demo dir as CWD — this also
# makes test behavior identical to `python -m rates serve`.
import os  # noqa: E402

os.chdir(Path(__file__).resolve().parent)
