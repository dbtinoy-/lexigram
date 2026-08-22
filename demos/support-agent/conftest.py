"""Pytest bootstrap for the support-agent demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import
``support_agent`` without installing (auth-web pattern):

    uv run pytest demos/support-agent/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
