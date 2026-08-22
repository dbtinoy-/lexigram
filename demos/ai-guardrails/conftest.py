"""Pytest bootstrap for the ai-guardrails demo.

Adds the demo's ``src`` directory to ``sys.path`` (auth-web pattern):

    uv run pytest demos/ai-guardrails/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
