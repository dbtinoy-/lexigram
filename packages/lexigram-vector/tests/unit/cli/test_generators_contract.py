"""Generator contract test for the vector CLI contributor."""

from __future__ import annotations

from pathlib import Path

from lexigram.testing.generators_contract import (
    assert_contributor_generators_render,
)
from lexigram.vector.cli.contributor import VectorCliContributor


def test_all_generators_render(tmp_path: Path) -> None:
    """Every declared generator renders into tmp_path."""
    count = assert_contributor_generators_render(
        VectorCliContributor(), tmp_path=tmp_path
    )
    assert count >= 1
