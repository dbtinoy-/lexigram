"""Enforce the stable/experimental tier boundary in the lexigram core repository.

Fails if any stable package (or the root workspace) references an experimental-tier
package in its declared project metadata: dependencies, optional-dependencies, or
dependency-groups.

Usage:
    python check_tier_boundary.py [--root PATH]
"""

import argparse
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.core.package_inventory import discover_package_paths

EXPERIMENTAL = {
    "lexigram-admin",
    "lexigram-ai",
    "lexigram-ai-agents",
    "lexigram-ai-evaluation",
    "lexigram-ai-feedback",
    "lexigram-ai-governance",
    "lexigram-ai-guard",
    "lexigram-ai-llm",
    "lexigram-ai-mcp",
    "lexigram-ai-memory",
    "lexigram-ai-observability",
    "lexigram-ai-prompt",
    "lexigram-ai-rag",
    "lexigram-ai-relay",
    "lexigram-ai-relay-gateway",
    "lexigram-ai-session",
    "lexigram-ai-skills",
    "lexigram-ai-workers",
    "lexigram-all",
    "lexigram-cli",
    "lexigram-multimedia",
    "lexigram-multimedia-beat",
    "lexigram-multimedia-image",
    "lexigram-multimedia-interpolate",
    "lexigram-multimedia-music",
    "lexigram-multimedia-tts",
    "lexigram-multimedia-upscale",
    "lexigram-multimedia-video",
    "lexigram-ui",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    root = Path(args.root)
    files = sorted([root / "pyproject.toml"]) + sorted(
        root / p / "pyproject.toml" for p in discover_package_paths(root)
    )
    files = [f for f in files if "lexigram-all" not in str(f)]
    bad = []
    for f in files:
        with open(f) as fh:
            text = fh.read()
        block = re.sub(r"^\s*#.*$", "", text, flags=re.M)
        for name in sorted(EXPERIMENTAL):
            if re.search(rf'"{name}(?:[\[>=<]|")', block):
                bad.append((f, name))
    if bad:
        for f, name in bad:
            print(f"TIER VIOLATION: {f} references experimental {name}")
        return 1
    print(f"tier boundary OK ({len(files)} pyproject files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
