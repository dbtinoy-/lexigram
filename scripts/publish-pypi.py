from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.core.package_inventory import discover_package_paths

ROOT = Path.cwd().resolve()

# NOTE: lexigram-admin and lexigram-ai-governance contain internal-IP references —
# sanitize these before publishing to PyPI.

PUBLISH_ORDER: tuple[tuple[str, ...], ...] = (
    ("lexigram-contracts",),
    ("lexigram",),
    tuple(
        p.name
        for p in discover_package_paths(ROOT)
        if p.name not in ("lexigram-contracts", "lexigram")
    ),
)


def find_packages(include: list[str] | None = None) -> list[str]:
    pkgs = []
    for p in discover_package_paths(ROOT):
        if include and p.name not in include:
            continue
        pkgs.append(p.name)
    return pkgs


def member_path(name: str) -> Path:
    """Resolve a package name to its workspace-relative directory."""
    for p in discover_package_paths(ROOT):
        if p.name == name:
            return p
    return Path(name)


def test_package(name: str, *, uv: str) -> bool:
    pkg_dir = ROOT / member_path(name)
    test_dir = pkg_dir / "tests"
    if not test_dir.is_dir():
        print(f"  no tests directory, skipping")
        return True
    ignore_integration = []
    if (pkg_dir / "tests" / "integration").is_dir():
        ignore_integration = ["--ignore", str(pkg_dir / "tests" / "integration")]
    result = subprocess.run(
        [uv, "run", "pytest", str(test_dir), "-q", "--tb=short", "-x",
         "--cov-fail-under=0", *ignore_integration],
        cwd=ROOT,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"\n  FAILED tests {name}:")
        for line in result.stdout.strip().splitlines()[-5:]:
            print(f"    {line}")
        for line in result.stderr.strip().splitlines()[-3:]:
            print(f"    {line}")
        return False
    # Print last line of test output (summary)
    summary = [l for l in result.stdout.strip().splitlines() if l][-1]
    print(f"  {summary}")
    return True


def build_package(name: str, *, uv: str) -> Path:
    wheel_prefix = name.replace("-", "_") + "-"
    result = subprocess.run(
        [uv, "build", "--package", name],
        cwd=ROOT,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  FAILED build {name}: {result.stderr.strip()}")
        return None
    matches = sorted(
        ROOT / "dist" / f for f in os.listdir(ROOT / "dist")
        if f.endswith(".whl") and f.startswith(wheel_prefix)
    )
    if not matches:
        print(f"  FAILED to find wheel for {name}")
        return None
    return matches[-1]


def already_published(name: str) -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "index", "versions", name],
        capture_output=True, text=True,
    )
    return "0.1.1" in result.stdout


def publish_package(wheel: Path, *, uv: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"  [dry-run] would publish {wheel.name}")
        return True
    delay = 10
    for attempt in range(10):
        result = subprocess.run(
            [uv, "publish", str(wheel)],
            cwd=ROOT,
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return True
        msg = result.stderr.strip()
        if "already exists" in msg.lower():
            print(f"already on PyPI")
            return True
        if "429" in msg or "Too Many" in msg:
            print(f"rate limited, retrying in {delay}s...", end=" ", flush=True)
            time.sleep(delay)
            delay = min(delay + 15, 120)
            continue
        print(f"  FAILED publish {wheel.name}: {msg}")
        return False
    print(f"  FAILED after retries")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(prog="publish-pypi")
    parser.add_argument("--dry-run", action="store_true", help="Build only, do not upload")
    parser.add_argument("--skip-tests", action="store_true", help="Skip tests before publishing")
    parser.add_argument("--packages", nargs="+", help="Specific packages to publish (default: all public)")
    args = parser.parse_args()

    uv = os.environ.get("UV", "uv")
    pkgs = find_packages(include=args.packages)
    built: dict[str, Path] = {}

    print(f"Testing {len(pkgs)} packages...")
    for pkg in pkgs:
        if args.skip_tests:
            print(f"  {pkg}: skipped")
            continue
        print(f"  Testing {pkg}...", end=" ", flush=True)
        if not test_package(pkg, uv=uv):
            print(f"  ABORTING — tests failed for {pkg}")
            return 1

    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        for f in dist_dir.iterdir():
            f.unlink()

    print(f"Building {len(pkgs)} packages (v0.1.1)...")
    for pkg in pkgs:
        print(f"  Building {pkg}...", end=" ", flush=True)
        wheel = build_package(pkg, uv=uv)
        if wheel is None:
            return 1
        built[pkg] = wheel
        print(f"{wheel.name}")

    if args.dry_run:
        print(f"\nDry-run complete. {len(built)} packages built successfully.")
        return 0

    token = os.environ.get("UV_PUBLISH_TOKEN")
    if not token:
        print("ERROR: UV_PUBLISH_TOKEN not set", file=sys.stderr)
        return 1

    print(f"\nPublishing {len(built)} packages to PyPI...")
    for phase in PUBLISH_ORDER:
        phase_pkgs = [p for p in phase if p in built]
        if not phase_pkgs:
            continue
        for i, pkg in enumerate(phase_pkgs):
            wheel = built[pkg]
            print(f"  Publishing {pkg} ({wheel.name})...", end=" ", flush=True)
            if not publish_package(wheel, uv=uv, dry_run=False):
                return 1
            print("done")
            if i < len(phase_pkgs) - 1:
                wait = 90 if pkg == "lexigram" else 30
                print(f"  Waiting {wait}s for rate limit...")
                time.sleep(wait)
        if phase_pkgs:
            print(f"  Waiting 15s for PyPI to index...")
            time.sleep(15)

    print(f"\nAll {len(built)} packages published successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
