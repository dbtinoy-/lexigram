"""Shared test configuration for lexigram-ai-memory tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow absolute imports of test helpers within tests/unit/
sys.path.insert(0, str(Path(__file__).parent / "unit"))
