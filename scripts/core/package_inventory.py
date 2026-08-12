from __future__ import annotations

from pathlib import Path
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - workspace requires >=3.11
    import tomli as tomllib


def discover_package_paths(root: Path | str) -> list[Path]:
    """Workspace member directories, relative to ``root``, sorted by package name.

    Driven by ``[tool.uv.workspace].members`` in the root ``pyproject.toml`` so
    that discovery stays correct regardless of how packages are grouped on disk.
    """

    root_path = Path(root)
    config = tomllib.loads((root_path / "pyproject.toml").read_text())
    members = config.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])

    found: dict[str, Path] = {}
    for pattern in members:
        for match in sorted(root_path.glob(pattern)):
            if match.is_dir() and (match / "pyproject.toml").exists():
                found[match.name] = match.relative_to(root_path)

    return [found[name] for name in sorted(found)]


def discover_packages(root: Path | str) -> list[str]:
    """Workspace member package names, sorted."""

    return [path.name for path in discover_package_paths(root)]