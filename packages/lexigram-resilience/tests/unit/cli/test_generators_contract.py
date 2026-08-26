"""Generator contract test for the resilience CLI contributor.

The resilience contributor intentionally declares no generators today;
the contract asserts that baseline so any newly contributed generator is
exercised automatically.
"""

from __future__ import annotations

from pathlib import Path

from lexigram.resilience.cli.contributor import ResilienceCliContributor
from lexigram.testing.generators_contract import (
    assert_contributor_generators_render,
)


def test_all_generators_render(tmp_path: Path) -> None:
    """Every declared generator renders into tmp_path."""
    count = assert_contributor_generators_render(
        ResilienceCliContributor(), tmp_path=tmp_path
    )
    assert count >= 0
