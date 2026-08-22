"""Pytest bootstrap for the feedback-loop demo (single shim — no UI).

    uv run pytest demos/feedback-loop/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
