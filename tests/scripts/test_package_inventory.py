"""Tests for package inventory discovery."""

# ruff: noqa: I001

from __future__ import annotations

from pathlib import Path

from scripts.core.package_inventory import discover_package_paths, discover_packages

REPO_ROOT = Path(__file__).resolve().parents[2]


def _workspace(tmp_path: Path, members: list[str]) -> Path:
    body = ",".join(f'"{m}"' for m in members)
    (tmp_path / "pyproject.toml").write_text(
        f"[tool.uv.workspace]\nmembers = [{body}]\n"
    )
    return tmp_path


def test_discover_packages_returns_every_workspace_member() -> None:
    assert len(discover_packages(REPO_ROOT)) == 54


def test_discover_packages_is_sorted_and_unique() -> None:
    packages = discover_packages(REPO_ROOT)

    assert packages == sorted(packages)
    assert len(packages) == len(set(packages))


def test_discover_packages_excludes_non_members() -> None:
    packages = discover_packages(REPO_ROOT)

    assert "lexigram_workspace.egg-info" not in packages
    assert all(not package.startswith(".") for package in packages)
    # lexigram-all is a directory but not a workspace member
    assert "lexigram-all" not in packages


def test_discover_package_paths_returns_paths_relative_to_root() -> None:
    paths = discover_package_paths(REPO_ROOT)

    assert len(paths) == 54
    assert all(not p.is_absolute() for p in paths)
    assert all((REPO_ROOT / p / "pyproject.toml").exists() for p in paths)


def test_globs_expand(tmp_path: Path) -> None:
    root = _workspace(tmp_path, ["core/*"])
    for name in ("lexigram", "lexigram-contracts"):
        pkg = root / "core" / name
        pkg.mkdir(parents=True)
        (pkg / "pyproject.toml").write_text("")

    assert discover_packages(root) == ["lexigram", "lexigram-contracts"]
    assert discover_package_paths(root) == [
        Path("core/lexigram"),
        Path("core/lexigram-contracts"),
    ]


def test_directories_without_pyproject_are_ignored(tmp_path: Path) -> None:
    root = _workspace(tmp_path, ["packages/*"])
    (root / "packages" / "lexigram-real").mkdir(parents=True)
    (root / "packages" / "lexigram-real" / "pyproject.toml").write_text("")
    (root / "packages" / "not-a-package").mkdir(parents=True)

    assert discover_packages(root) == ["lexigram-real"]