"""Structural compliance tests for lexigram-vector."""
from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PACKAGE_ROOT / "src/lexigram/vector"


def test_vector_uses_backends_for_protocol_implementations() -> None:
    assert (SRC_ROOT / "backends").exists()
    assert not (SRC_ROOT / "drivers").exists()


def test_vector_keeps_adapters_directory() -> None:
    assert (SRC_ROOT / "adapters/document_store.py").exists()
    assert (SRC_ROOT / "adapters/vector_store.py").exists()
