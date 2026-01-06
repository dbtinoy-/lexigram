from __future__ import annotations

from pathlib import Path


def discover_packages(root: Path | str) -> list[str]:
    """Discover top-level Lexigram package directories under a workspace root."""

    root_path = Path(root)
    packages = {
        entry.name
        for entry in root_path.iterdir()
        if entry.is_dir()
        and entry.name.startswith("lexigram")
        and not entry.name.startswith(".")
        and not entry.name.endswith(".egg-info")
    }
    return sorted(packages)
