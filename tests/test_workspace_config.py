"""The workspace config lists must not drift from the workspace members."""

from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

from scripts.core.package_inventory import discover_packages

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
MEMBERS = set(discover_packages(REPO_ROOT))


def _package_names(entries: list[str]) -> set[str]:
    """Package names in a path list, at whatever depth they appear.

    Layout-agnostic on purpose: this must keep working as entries go from
    ``lexigram-sql/src`` to ``packages/lexigram-sql/src`` during Phase 3.
    """

    names = set()
    for entry in entries:
        for segment in Path(entry).parts:
            if segment.startswith("lexigram"):
                names.add(segment)
                break
    return names


@pytest.mark.parametrize(
    ("label", "entries"),
    [
        ("mypy_path", CONFIG["tool"]["mypy"]["mypy_path"]),
        # testpaths must stay explicit: pytest rejects `pytest_plugins` in
        # non-top-level conftests when walking from tier roots (10 members hit).
        ("testpaths", CONFIG["tool"]["pytest"]["ini_options"]["testpaths"]),
    ],
)
def test_config_list_covers_every_workspace_member(label: str, entries: list[str]) -> None:
    missing = MEMBERS - _package_names(entries)

    assert not missing, f"{label} is missing workspace members: {sorted(missing)}"


def test_collapsed_lists_cover_all_tier_roots() -> None:
    """Collapsed lists must point at the tier roots, not individual packages.

    Coverage `source` is collapsed after Task 14; only `testpaths` and `mypy_path`
    still enumerate every package (pytest's `pytest_plugins` rule and mypy's lack
    of glob expansion both require explicit paths).
    """

    roots = {"core", "packages", "experimental"}

    assert roots <= set(CONFIG["tool"]["coverage"]["run"]["source"])
