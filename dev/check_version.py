"""Version drift check + bump for the Lexigram workspace.

Compares the local version in each package's pyproject.toml against the
latest version published on PyPI, and computes the next version following
the Lexigram scheme (AGENTS.md §3.6):

    0.<minor>.<patch><build>      e.g. 0.1.2, 0.1.3001, 0.1.3002

  * The last segment is <patch> with a zero-padded 3-digit <build>:
    "3001" -> patch=3, build=001.
  * A bare patch ("0.1.2") means build=0.
  * After publishing 0.Y.Z, the next version is 0.Y.<Z+1>001.
  * When PyPI is ahead of the local pyproject, bumping starts FROM the
    PyPI version so we never regress to an already-published version.

Commands:
  check [--pkg NAME ...]          Report local vs PyPI for each package.
                                  Exit code 1 when any package is UNPUBLISHED
                                  or BEHIND (bump needed). CI-gate friendly.
  bump [--pkg NAME ...]           Show the next version per package.
       [--bump build|patch|minor] Which segment to bump (default: build).
       [--apply]                  Write the new version into pyproject.toml.
       [--publish]                Also run that package's unit tests
                                  (integration excluded) before applying.

Per-package publish flow (no all-package test runs):
    env -u PYTHONPATH uv run pytest <pkg>/tests -q --tb=short -m "not integration"
    uv build --package <pkg>
    uv publish dist/<wheel>
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

import argparse
import json  # noqa: TID251 — standalone publish tool; runs before workspace imports
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request


from dev.core.package_inventory import discover_package_paths

PYPI_URL = "https://pypi.org/pypi/{name}/json"


def workspace_members() -> list[str]:
    """All workspace member package names, sorted."""
    return sorted(p.name for p in discover_package_paths(ROOT))


def member_path(name: str) -> Path:
    """Resolve a package name to its workspace-relative directory."""
    for p in discover_package_paths(ROOT):
        if p.name == name:
            return p
    return Path(name)


def local_version(name: str) -> str | None:
    """Version declared in the package's pyproject.toml."""
    path = ROOT / member_path(name) / "pyproject.toml"
    if not path.is_file():
        return None
    match = re.search(r'^version\s*=\s*"([^"]+)"', path.read_text(), re.MULTILINE)
    return match.group(1) if match else None


def pypi_latest(name: str) -> str | None:
    """Latest published version on PyPI, or None when unknown/unreachable."""
    try:
        with urllib.request.urlopen(PYPI_URL.format(name=name), timeout=15) as resp:
            data = json.load(resp)
        return data["info"]["version"]
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    except Exception:
        return None


def split_version(version: str) -> tuple[int, int, int]:
    """Return (minor, patch, build) from a Lexigram version string."""
    parts = version.split(".")
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    tail = parts[2] if len(parts) > 2 and parts[2].isdigit() else "0"
    value = int(tail)
    if value >= 1000:
        patch, build = value // 1000, value % 1000
    else:
        patch, build = value, 0
    return minor, patch, build


def format_version(minor: int, patch: int, build: int) -> str:
    return f"0.{minor}.{patch}" if build == 0 else f"0.{minor}.{patch}{build:03d}"


def next_version(version: str, bump: str = "build") -> str:
    """Next version following the Lexigram scheme from the given base."""
    minor, patch, build = split_version(version)
    if bump == "minor":
        return format_version(minor + 1, 1, 1)
    if bump == "patch":
        return format_version(minor, patch + 1, 1)
    # build (default): a bare patch (build=0) starts its own build series
    # at 001 — e.g. local 0.1.4 bumps to 0.1.4001, NOT to the next patch.
    if build == 0:
        return format_version(minor, patch, 1)
    return format_version(minor, patch, build + 1)


def version_key(version: str) -> tuple[int, int, int]:
    return split_version(version)


def state_of(local: str | None, pypi: str | None) -> str:
    if local is None:
        return "NO-PYPROJECT"
    if pypi is None:
        return "UNPUBLISHED"
    if local == pypi:
        return "SYNCED"
    if version_key(local) > version_key(pypi):
        return "AHEAD"
    return "BEHIND"


def run_unit_tests(name: str) -> bool:
    """Unit tests for one package only (integration excluded)."""
    test_dir = ROOT / member_path(name) / "tests"
    if not test_dir.is_dir():
        print(f"  {name}: no tests directory")
        return True
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_dir),
            "-q",
            "--tb=short",
            "-m",
            "not integration",
            "--no-cov",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"  {name}: TESTS FAILED\n{result.stdout[-500:]}")
        return False
    summary = [line for line in result.stdout.splitlines() if line][-1]
    print(f"  {name}: {summary}")
    return True


def apply_version(name: str, version: str) -> bool:
    path = ROOT / member_path(name) / "pyproject.toml"
    text = path.read_text()
    new_text = re.sub(
        r'(^version\s*=\s*)"[^"]+"',
        rf'\g<1>"{version}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if new_text == text:
        print(f"  {name}: version line not found, no change")
        return False
    path.write_text(new_text)
    print(f"  {name}: pyproject.toml version -> {version}")
    return True


def cmd_check(names: list[str]) -> int:
    rows = [(n, local_version(n), pypi_latest(n)) for n in names]
    local_w = max(len(r[1] or "-") for r in rows)
    pypi_w = max(len(r[2] or "-") for r in rows)
    print(f"{'PACKAGE':<34}{'LOCAL':<{local_w + 3}}{'PYPI':<{pypi_w + 3}}STATE")
    for name, local, pypi in rows:
        state = state_of(local, pypi)
        print(
            f"{name:<34}{local or '-':<{local_w + 3}}{pypi or '-':<{pypi_w + 3}}{state}"
        )
    needed = [
        name
        for name, local, pypi in rows
        if state_of(local, pypi) in ("UNPUBLISHED", "BEHIND")
    ]
    if needed:
        print(f"\n{len(needed)} package(s) need a bump: {', '.join(needed)}")
        print("Run: uv run python scripts/check_version.py bump --pkg <name> --apply")
        return 1
    return 0


def cmd_bump(names: list[str], bump: str, apply: bool, publish: bool) -> int:
    for name in names:
        local = local_version(name)
        pypi = pypi_latest(name)
        if local is None and pypi is None:
            print(f"  {name}: no pyproject, skipping")
            continue
        base = max(local or "0.1.0", pypi or "0.1.0", key=version_key)
        nxt = next_version(base, bump)
        print(f"{name}: local={local or '-'} pypi={pypi or '-'} -> next {nxt}")
        if publish and not run_unit_tests(name):
            continue
        if apply:
            apply_version(name, nxt)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="check_version")
    sub = parser.add_subparsers(dest="command", required=True)

    check_p = sub.add_parser("check", help="local vs PyPI report")
    check_p.add_argument("--pkg", nargs="+", default=None)

    bump_p = sub.add_parser("bump", help="show/apply next version")
    bump_p.add_argument("--pkg", nargs="+", default=None)
    bump_p.add_argument("--bump", choices=["build", "patch", "minor"], default="build")
    bump_p.add_argument("--apply", action="store_true", help="write pyproject.toml")
    bump_p.add_argument(
        "--publish", action="store_true", help="run unit tests before applying"
    )
    args = parser.parse_args()

    names = args.pkg or workspace_members()

    if args.command == "check":
        return cmd_check(names)
    if args.command == "bump":
        return cmd_bump(names, args.bump, args.apply, args.publish)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
