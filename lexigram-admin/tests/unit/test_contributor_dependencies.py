"""Tests for contributor dependency sorting."""

from __future__ import annotations

import pytest


class _Contributor:
    def __init__(self, name: str, depends_on: tuple[str, ...] = ()) -> None:
        self.name = name
        self.depends_on = depends_on


def test_contributors_sorted_by_dependency_order() -> None:
    from lexigram.contracts.admin.dependencies import sort_contributors

    ordered = sort_contributors([
        _Contributor("core", ("cache",)),
        _Contributor("search", ("cache",)),
        _Contributor("cache"),
    ])
    assert [c.name for c in ordered] == ["cache", "core", "search"]


def test_missing_dependency_is_configuration_error() -> None:
    from lexigram.contracts.admin.dependencies import ContributorDependencyError, sort_contributors

    with pytest.raises(ContributorDependencyError, match="missing dependency"):
        sort_contributors([_Contributor("search", ("cache",))])


def test_dependency_cycle_is_configuration_error() -> None:
    from lexigram.contracts.admin.dependencies import ContributorDependencyError, sort_contributors

    with pytest.raises(ContributorDependencyError, match="cycle"):
        sort_contributors([
            _Contributor("a", ("b",)),
            _Contributor("b", ("a",)),
        ])
