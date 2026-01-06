"""Structural compliance tests for admin source layout."""

from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PACKAGE_ROOT / "src/lexigram/admin"


def test_admin_has_no_src_testing_shim() -> None:
    """Ensure the source tree does not re-export testing helpers."""
    assert not (SRC_ROOT / "testing").exists()
