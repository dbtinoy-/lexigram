"""Structural compliance tests for the package layout."""
from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PACKAGE_ROOT / "src/lexigram/resilience"


def test_package_uses_idempotency_durable_provider() -> None:
    assert (SRC_ROOT / "idempotency" / "durable_provider.py").exists()
    assert not (SRC_ROOT / "idempotency_durable_provider.py").exists()
