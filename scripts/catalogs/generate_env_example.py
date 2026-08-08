#!/usr/bin/env python3
"""Generate .env.example from docs/lexigram-docs/reference/REF_ENV_VARS.md.

Usage:
    python scripts/catalogs/generate_env_example.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/lexigram-docs/reference/REF_ENV_VARS.md"
OUT = ROOT / ".env.example"

ROW = re.compile(r"^\| `([A-Z][A-Z0-9_]*)` \| (\S[^|]*) \| ([^|]*) \| ([^|]*) \| (.*) \|$")
PKG_HEADER = re.compile(r"^### `([^`]+)` \((\d+) vars\)$")

# Prefill sensible values for services the docker-compose provides.
SERVICE_DEFAULTS = {
    "LEX_SQL__BACKEND__URL": "postgresql://lexigram:lexigram@localhost:5432/lexigram",
    "LEX_TASKS__BACKEND__REDIS_URL": "redis://localhost:6379/0",
    "LEX_TASKS__REDIS_URL": "redis://localhost:6379/0",
    "LEX_TEST_REDIS_URL": "redis://localhost:6379/0",
    "LEX_TESTING__REDIS_URL": "redis://localhost:6379/0",
    "LEX_CACHE__BACKENDS__REDIS__URL": "redis://localhost:6379/0",
    "LEX_AUTH__JWT__SECRET": "change-me-in-production",
    "LEX_WEB__SECURITY__CSRF__SECRET_KEY": "change-me-in-production",
    "LEX_SQL__AUDIT_HMAC_KEY": "change-me-in-production",
    "LEX_DEBUG": "false",
    "LEX_ENV": "development",
    "LEX_PROFILE": "development",
    "LEX_QUIET": "false",
}
# Vars that should be flagged as required secrets, not left blank.
SECRET_SUFFIX = (
    "SECRET", "SECRET_KEY", "API_KEY", "PASSWORD", "TOKEN", "HMAC_KEY",
    "CREDENTIALS", "PRIVATE_KEY",
)


def parse(catalog: Path) -> list[tuple[str, list[tuple[str, str, str]]]]:
    sections: list[tuple[str, list[tuple[str, str, str]]]] = []
    current: tuple[str, list[tuple[str, str, str]]] | None = None
    for line in catalog.read_text().splitlines():
        if m := PKG_HEADER.match(line):
            if current:
                sections.append(current)
            current = (m.group(1), [])
        elif current and (m := ROW.match(line)):
            name, typ, _default, desc, _src = m.groups()
            current[1].append((name, typ.strip(), desc.strip()))
    if current:
        sections.append(current)
    return sections


def generate() -> None:
    """Write .env.example from the env var catalog."""
    sections = parse(CATALOG)
    lines = [
        "# Lexigram Framework environment configuration example.",
        "#",
        "# Copy to .env and adjust values for your deployment:",
        "#   cp .env.example .env",
        "#",
        "# Generated from docs/lexigram-docs/reference/REF_ENV_VARS.md by",
        "# scripts/catalogs/generate_env_example.py — do not edit by hand.",
        "#",
        "# All variables are optional unless noted: every config value carries a",
        "# code default, so an unset variable falls back to framework defaults.",
        "#",
        "# Critical secrets MUST be set in production:",
        "#   * any value shown as <change-me-in-production>",
        "#   * provider API keys (OpenAI, Anthropic, Google, ...) supplied through",
        "#     your secrets manager or LEX_*_SECRET_NAME references",
    ]
    for pkg, rows in sections:
        lines.append("")
        lines.append(f"# ── {pkg} ──")
        for name, typ, desc in rows:
            default = SERVICE_DEFAULTS.get(name)
            if default:
                val = default
            elif name.endswith(SECRET_SUFFIX) or "SECRET" in name or "API_KEY" in name:
                val = "<change-me-in-production>"
            else:
                val = ""
            comment = f"  # {typ}" if typ else ""
            if desc:
                comment = f"  # {desc} ({typ})" if typ else f"  # {desc}"
            lines.append(f"{name}={val}{comment}")

    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT} with {len(sections)} package sections, {sum(len(r) for _, r in sections)} vars")


if __name__ == "__main__":
    generate()