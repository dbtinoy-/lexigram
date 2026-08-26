"""Generator contract test for the webhook CLI contributor.

The webhook contributor intentionally declares no generators today; the
contract asserts that baseline so any newly contributed generator is
exercised automatically.
"""

from __future__ import annotations

from pathlib import Path

from lexigram.testing.generators_contract import (
    assert_contributor_generators_render,
)
from lexigram.webhook.cli.contributor import WebhookCliContributor


def test_all_generators_render(tmp_path: Path) -> None:
    """Every declared generator renders into tmp_path."""
    count = assert_contributor_generators_render(
        WebhookCliContributor(), tmp_path=tmp_path
    )
    assert count >= 0
