"""Structural compliance tests for lexigram-search."""

from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PACKAGE_ROOT / "src/lexigram/search"


def test_search_uses_lib_not_utils() -> None:
    assert (SRC_ROOT / "lib").exists()
    assert not (SRC_ROOT / "utils").exists()


def test_search_uses_single_engine_surface() -> None:
    assert (SRC_ROOT / "engine").exists()
    assert not (SRC_ROOT / "core").exists()
