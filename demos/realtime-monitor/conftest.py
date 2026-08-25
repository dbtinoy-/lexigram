"""Pytest bootstrap for the realtime-monitor demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install. Demo packages are intentionally
excluded from the monorepo aggregate test run (see root ``pyproject.toml``
``norecursedirs``), so these tests are run explicitly:

    uv run pytest demos/realtime-monitor/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import os  # noqa: E402

os.chdir(Path(__file__).resolve().parent)
