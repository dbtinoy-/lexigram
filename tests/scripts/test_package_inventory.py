"""Tests for package inventory discovery."""

# ruff: noqa: I001

from __future__ import annotations

from pathlib import Path

from scripts.core.package_inventory import discover_packages


def test_discover_packages_excludes_egg_info_hidden_dirs_and_is_unique() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    packages = discover_packages(repo_root)

    assert "lexigram_workspace.egg-info" not in packages
    assert all(not package.startswith(".") for package in packages)
    assert packages == sorted(packages)
    assert len(packages) == len(set(packages))


def test_discover_packages_excludes_hidden_top_level_directories(tmp_path: Path) -> None:
    (tmp_path / "lexigram").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "lexigram_workspace.egg-info").mkdir()

    packages = discover_packages(tmp_path)

    assert packages == ["lexigram"]
