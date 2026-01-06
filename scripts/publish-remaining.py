"""Publish remaining 19 packages to PyPI (run when quota resets)."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
WAIT = 180  # 3 min between new projects
RETRY_BASE = 300  # 5 min initial retry delay

REMAINING = [
    "lexigram-ai-observability",
    "lexigram-ai-rag",
    "lexigram-ai-skills",
    "lexigram-ai-workers",
    "lexigram-audit",
    "lexigram-cli",
    "lexigram-features",
    "lexigram-graph",
    "lexigram-http",
    "lexigram-notification",
    "lexigram-queue",
    "lexigram-resilience",
    "lexigram-secrets",
    "lexigram-sql",
    "lexigram-tenancy",
    "lexigram-testing",
    "lexigram-ui",
    "lexigram-vector",
    "lexigram-webhook",
    "lexigram-workflow",
]


def already_published(name: str) -> bool:
    r = subprocess.run(
        [sys.executable, "-m", "pip", "index", "versions", name],
        capture_output=True, text=True,
    )
    return "0.1.1" in r.stdout


def main() -> int:
    token = os.environ.get("UV_PUBLISH_TOKEN") or os.environ.get("PYPI_TOKEN")
    if not token:
        print("ERROR: Set UV_PUBLISH_TOKEN or PYPI_TOKEN", file=sys.stderr)
        return 1

    os.chdir(ROOT)
    total = len(REMAINING)
    published = 0
    skipped = 0

    for i, pkg in enumerate(REMAINING):
        prefix = pkg.replace("-", "_")
        wheels = sorted(f for f in os.listdir(DIST) if f.endswith(".whl") and f.startswith(prefix))
        if not wheels:
            print(f"[{i+1}/{total}] SKIP {pkg} — no wheel found")
            skipped += 1
            continue
        wheel = str(DIST / wheels[-1])

        if already_published(pkg):
            print(f"[{i+1}/{total}] OK {pkg} — already on PyPI")
            published += 1
            continue

        for attempt in range(10):
            print(f"[{i+1}/{total}] Publishing {pkg}...", end=" ", flush=True)
            r = subprocess.run(
                ["uv", "publish", "--token", token, wheel],
                capture_output=True, text=True,
            )
            if r.returncode == 0:
                print("OK")
                published += 1
                break
            err = r.stderr.strip()
            if "already exists" in err.lower():
                print("already on PyPI")
                published += 1
                break
            if "429" in err:
                delay = RETRY_BASE * (attempt + 1)
                print(f"rate limited, retry in {delay}s...")
                time.sleep(delay)
            else:
                print(f"FAILED: {err[-200:]}")
                return 1
        else:
            print(f"GIVING UP on {pkg} after 10 retries")
            return 1

        if i < total - 1:
            print(f"  Waiting {WAIT}s...")
            time.sleep(WAIT)

    print(f"\nDone. {published} published, {skipped} skipped, {total - published - skipped} failed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
