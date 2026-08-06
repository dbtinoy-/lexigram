from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path.cwd().resolve()

# NOTE: lexigram-admin and lexigram-ai-governance contain internal-IP references —
# sanitize before ever publishing them to PyPI (the GitHub mirror script does this).

# Patterns that must never ship to PyPI. Keyed by descriptive name so scan
# output explains what tripped: private network addresses, placeholder
# secrets, and internal-only hostnames.
SENSITIVE_PATTERNS: dict[str, re.Pattern[str]] = {
    "private-ipv4": re.compile(
        r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}|169\.254\.\d{1,3}\.\d{1,3})\b"
    ),
    "weak-placeholder-secret": re.compile(
        r"\b(change-me(-in-production)?|your-secret-(key|hmac)|"
        r"replace-this-secret|pypi-[A-Za-z0-9_-]{8,})\b",
        re.IGNORECASE,
    ),
    # Internal-only hostnames: either a URL host (case-insensitive), or a
    # bare single-label hostname ending in .internal/.corp/.lan. Bare hosts
    # are matched case-sensitively against lowercase — hostnames surface in
    # configs as lowercase, while uppercase variants are near-always enum
    # members (e.g. OTel `SpanKind.INTERNAL`), which are not hostnames.
    # Bare `.local` is excluded — it is a valid mDNS suffix AND matches
    # Python module paths (`lexigram.features.backends.local`), the
    # dominant false-positive class with no leak-signal.
    "internal-hostname": re.compile(
        r"(?:(?i:https?://[\w-]+(?:\.[\w-]+)*\.(?:internal|corp|local|lan)"
        r"(?=[:/?#\s\"']|$))|"
        r"(?<![\w.])[a-z0-9-]+\.(?:internal|corp|lan)(?![\w-]))"
    ),
}

_TEXT_SUFFIXES = (
    ".py", ".md", ".txt", ".rst", ".toml", ".yaml", ".yml", ".json",
    ".cfg", ".ini", ".html", ".csv",
)

# Scoped allowlist for content that must exist inside the codebase by design:
# values the code itself detects and rejects. Entry format is
# (file-suffix, pattern-name): file paths are matched by endswith, so a hit is
# only forgiven when BOTH the file and the pattern are exactly as approved.
# Adding entries here is a security decision — keep it minimal and documented.
SENSITIVE_ALLOWLIST: dict[tuple[str, str], str] = {
    (
        "lexigram/contracts/security/url_safety.py",
        "private-ipv4",
    ): "SSRF guard blocklist — private ranges the code actively blocks",
    (
        "lexigram/auth/authn/jwt.py",
        "weak-placeholder-secret",
    ): "values JWTTokenManager rejects (change-me-in-production blocklist)",
    (
        "lexigram/auth/config.py",
        "weak-placeholder-secret",
    ): "values JWTConfig rejects in strict environments",
    (
        "lexigram/config/constants.py",
        "weak-placeholder-secret",
    ): "values secret validation rejects as weak",
    (
        "lexigram/config/secrets.py",
        "weak-placeholder-secret",
    ): "values secret validation rejects as weak",
    (
        "lexigram/admin/config.py",
        "weak-placeholder-secret",
    ): "fail-closed session_secret placeholder + values AdminAuthConfig rejects in production",
    (
        "lexigram/admin/di/sub_providers/auth.py",
        "weak-placeholder-secret",
    ): "session_secret fallbacks mirror the fail-closed placeholder AdminAuthConfig rejects",
    (
        "lexigram/ai/config.py",
        "weak-placeholder-secret",
    ): "insecure_defaults list that AI config rejects",
    (
        "lexigram/cache/constants.py",
        "weak-placeholder-secret",
    ): "values secret validation rejects as weak",
    (
        "lexigram/cli/registry/config.py",
        "weak-placeholder-secret",
    ): "placeholder values CLI config rejects",
    (
        "lexigram/cli/registry/template.py",
        "weak-placeholder-secret",
    ): "scaffold template placeholder — strict-mode validation forces replacement",
    (
        "lexigram/storage/config.py",
        "weak-placeholder-secret",
    ): "docstring of the placeholder-credentials rejection logic",
    (
        "lexigram/storage/constants.py",
        "weak-placeholder-secret",
    ): "values secret validation rejects as weak",
}

PUBLISH_ORDER: tuple[tuple[str, ...], ...] = (
    ("lexigram-contracts",),
    ("lexigram",),
    tuple(
        p for p in sorted(
            d.name for d in ROOT.iterdir()
            if d.is_dir() and d.name.startswith("lexigram")
            and d.name not in ("lexigram-contracts", "lexigram")
            and not d.name.endswith(".egg-info")
        )
    ),
)


def find_packages(include: list[str] | None = None) -> list[str]:
    pkgs = []
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or not d.name.startswith("lexigram"):
            continue
        if d.name.endswith(".egg-info"):
            continue
        if include and d.name not in include:
            continue
        pkgs.append(d.name)
    return pkgs


def test_package(name: str, *, uv: str) -> bool:
    pkg_dir = ROOT / name
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


def scan_artifact(wheel: Path) -> tuple[list[str], list[str]]:
    """Scan a built wheel for content that must not ship to PyPI.

    Returns (violations, allowlisted): block on violations; allowlisted
    matches carry their justification and are reported for transparency.
    Capped to keep output readable.
    """
    violations: list[str] = []
    allowlisted: list[str] = []
    try:
        with zipfile.ZipFile(wheel) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                suffix = Path(info.filename).suffix.lower()
                if suffix not in _TEXT_SUFFIXES:
                    continue
                try:
                    data = zf.read(info.filename).decode("utf-8", errors="ignore")
                except (OSError, zipfile.BadZipFile):
                    continue
                for name, pattern in SENSITIVE_PATTERNS.items():
                    if not pattern.search(data):
                        continue
                    reason = SENSITIVE_ALLOWLIST.get((info.filename, name))
                    if reason:
                        allowlisted.append(
                            f"{wheel.name}: {info.filename}: {name} "
                            f"[allowlisted: {reason}]"
                        )
                    else:
                        violations.append(
                            f"{wheel.name}: {info.filename}: {name}"
                        )
                    break
                if len(violations) >= 30:
                    return violations, allowlisted
    except (OSError, zipfile.BadZipFile) as e:
        violations.append(f"{wheel.name}: cannot scan: {e}")
    return violations, allowlisted


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
    parser.add_argument("--allow-sensitive", action="store_true",
                        help="Skip the sensitive-content scan (use only when whitelisting is impossible)")
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

    print(f"Building {len(pkgs)} packages...")
    for pkg in pkgs:
        print(f"  Building {pkg}...", end=" ", flush=True)
        wheel = build_package(pkg, uv=uv)
        if wheel is None:
            return 1
        built[pkg] = wheel
        print(f"{wheel.name}")

    if not args.allow_sensitive:
        print("Scanning built wheels for sensitive content...")
        blocked = False
        for pkg, wheel in built.items():
            violations, allowlisted = scan_artifact(wheel)
            for line in allowlisted:
                print(f"  allowlisted: {line}")
            if violations:
                blocked = True
                print(f"  SENSITIVE CONTENT in {pkg}:")
                for v in violations:
                    print(f"    {v}")
        if blocked:
            print(
                "\nABORTING — sensitive content detected in built artifacts. "
                "Sanitize the sources before publishing (or use --allow-sensitive "
                "only if the matches are false positives).",
                file=sys.stderr,
            )
            return 1
        print("  clean: no unallowlisted sensitive content in any built wheel.")

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
