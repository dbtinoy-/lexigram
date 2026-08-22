"""Tests over the versioned prompt store wrapper."""

from __future__ import annotations

import pytest

from prompt_lab.repository.templates import TEMPLATES
from prompt_lab.services.versioning import LabVersions


@pytest.fixture
def versions() -> LabVersions:
    lv = LabVersions(max_versions=10)
    lv.seed(TEMPLATES)
    return lv


class TestLabVersions:
    def test_seed_pushes_three_revisions(self, versions) -> None:
        assert len(versions.history("v1")) == 1
        assert len(versions.history("v2")) == 2

    def test_active_defaults_to_latest(self, versions) -> None:
        rev, _tpl = versions.active("v2")
        assert rev == 2

    def test_get_revision_fetches_specific(self, versions) -> None:
        _rev, first = versions.get_revision("v2", 1)
        text = str(first.render(issue="x", tone="y"))
        assert "even more warmth" not in text.lower()

    def test_rollback_moves_pointer_back(self, versions) -> None:
        new_rev = versions.rollback("v2", steps=1)
        assert new_rev == 1

    def test_history_entries_have_rev_and_current_flag(
        self, versions,
    ) -> None:
        entries = versions.history("v2")
        entry = entries[-1]
        assert isinstance(entry["rev"], int)
        assert {"rev", "current", "metadata"} <= set(entry)
        assert entry["current"] is True  # latest seeded rev is active

    def test_unknown_variant_raises_key_error(self, versions) -> None:
        with pytest.raises(KeyError):
            versions.active("nope")
