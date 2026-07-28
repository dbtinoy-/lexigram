"""Structural compliance tests for the package layout."""
from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PACKAGE_ROOT / "src/lexigram/ai/observability"


def test_package_uses_health_not_health_pkg() -> None:
    assert (SRC_ROOT / "health").exists()
    assert not (SRC_ROOT / "health_pkg").exists()
