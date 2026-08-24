"""Pytest bootstrap for the llm-reproducibility demo.

Puts the demo ``src`` directory on ``sys.path`` so tests can import the
``llm_reproducibility`` package (the same way ``run_experiment.py`` does). Demo
packages are intentionally excluded from the monorepo aggregate test run
(see root ``pyproject.toml`` ``norecursedirs``), so these tests run via
``make test-demos`` or:

    uv run pytest demos/llm-reproducibility/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
