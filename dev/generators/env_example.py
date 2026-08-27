#!/usr/bin/env python3
"""Generate .env.example from docs/reference/REF_ENV_VARS.md.

Usage:
    python scripts/catalogs/generate_env_example.py
"""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/reference/REF_ENV_VARS.md"
OUT = ROOT / ".env.full.example"

ROW = re.compile(r"^`([A-Z][A-Z0-9_]*)`$")


def _split_cells(line: str) -> list[str]:
    """Split a catalog table row into cells, preserving escaped pipes.

    Catalog cells escape literal pipes as ``\\|`` (e.g. ``str \\| None``).
    A plain ``|`` is always a column separator, so splitting on pipes that are
    NOT preceded by a backslash is correct.  The backslash escape is then
    removed so types render as ``str | None``.

    Args:
        line: A ``| ... |`` table row.

    Returns:
        The unescaped cell contents with surrounding whitespace removed.
    """
    cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
    return [c.replace("\\|", "|") for c in cells]


# Patterns indicating the raw default is not a simple resolvable literal.
_UNRESOLVABLE = re.compile(r"[()\[\]{}]|const\.|tasks_const\.")
_DURATION = re.compile(r"^Duration\.(seconds|minutes|hours|days)\((\d+(?:\.\d+)?)\)$")
_UNIT_ABBREV = {"seconds": "s", "minutes": "m", "hours": "h", "days": "d"}


def _resolve_default(raw: str) -> str:
    """Convert a catalog default value to an env-file string.

    Returns an empty string when the default cannot be statically resolved
    (complex expressions, framework types with constant arguments,
    constant references, or ``None``).
    """
    if not raw or raw in {"—", "(complex)"}:
        return ""
    # Duration.seconds(30) → 30s, Duration.hours(1) → 1h, etc.
    if m := _DURATION.match(raw):
        unit = _UNIT_ABBREV[m.group(1)]
        return f"{m.group(2)}{unit}"
    # SecretStr('') → empty string; SecretStr('x') → x
    if raw.startswith("SecretStr(") and raw.endswith(")"):
        inner = raw[len("SecretStr(") : -1]
        if len(inner) >= 2 and inner[0] in ("'", '"') and inner[-1] == inner[0]:
            return inner[1:-1]
        return ""
    # Reject anything that looks like a Python expression or constant reference.
    if _UNRESOLVABLE.search(raw):
        return ""
    # Boolean normalization.
    if raw == "True":
        return "true"
    if raw == "False":
        return "false"
    # None means no default.
    if raw == "None":
        return ""
    # Strip surrounding quotes.
    if len(raw) >= 2 and raw[0] in ("'", '"') and raw[-1] == raw[0]:
        return raw[1:-1]
    return raw


def parse(catalog: Path) -> list[tuple[str, list[tuple[str, str, str, str]]]]:
    sections: list[tuple[str, list[tuple[str, str, str, str]]]] = []
    current: tuple[str, list[tuple[str, str, str, str]]] | None = None
    for line in catalog.read_text().splitlines():
        if m := PKG_HEADER.match(line):
            if current:
                sections.append(current)
            current = (m.group(1), [])
        elif current and line.strip().startswith("|") and line.strip().endswith("|"):
            cells = _split_cells(line)
            if len(cells) < 5:  # noqa: PLR2004
                continue
            name_match = ROW.match(cells[0])
            if not name_match:
                continue
            name = name_match.group(1)
            typ = cells[1].strip()
            default = cells[2].strip()
            desc = cells[3].strip()
            current[1].append((name, typ, default, desc))
    if current:
        sections.append(current)
    return sections


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
    "SECRET",
    "SECRET_KEY",
    "API_KEY",
    "PASSWORD",
    "TOKEN",
    "HMAC_KEY",
    "CREDENTIALS",
    "PRIVATE_KEY",
)

# Env vars read directly in source (os.getenv / os.environ) that are NOT
# part of the LEX_* config catalog. Kept here so .env.example regeneration
# is lossless. Name -> (placeholder value, inline comment).
SUPPLEMENTAL_VARS: dict[str, tuple[str, str]] = {
    "ADMIN_BASE": ("http://127.0.0.1:9003", "lexigram-admin e2e test base URL"),
    "ADMIN_SETUP_TOKEN": ("changeme", "lexigram-admin boot token (integration/CI)"),
    "ANTHROPIC_API_KEY": ("sk-ant-changeme", "Anthropic provider key (AI doctor)"),
    "APNS_KEY_PATH": ("", "Apple push notification key path"),
    "APP_ENV": ("development", "generic app environment read"),
    "AUDIT_HMAC_KEY": ("changeme", "audit doctor / signing key"),
    "AUTH_JWT_SECRET": ("changeme", "lexigram-auth JWT secret"),
    "AUTH_SECRET": ("changeme", "lexigram-cli environment validation"),
    "LEX_CONFIG_ALLOW_UNKNOWN": (
        "false",
        "bypass strict unknown-key errors (true/false)",
    ),
    "OAUTH_CLIENT_SECRET": ("change-me-oauth-client-secret", "app startup secret hook"),
    "BROKER_URL": ("amqp://guest:guest@localhost:5672//", "queue doctor broker URL"),
    "DATABASE_URL": (
        "postgresql://lexigram:lexigram@localhost:5432/lexigram",
        "SQL doctor / DB URL",
    ),
    "ENVIRONMENT": ("development", "legacy app-environment compatibility reads"),
    "F5_TTS_REFERENCE_ROOT": ("", "multimedia-tts reference audio root"),
    "FCM_SERVER_KEY": ("changeme", "Firebase Cloud Messaging key"),
    "JWT_SECRET": ("changeme", "app startup secret hook (JWT signing)"),
    "LEXIGRAM_EXPERIMENT_SEED": ("", "demos/llm-experiment seed"),
    "LEXI_SECRET": ("changeme", "secrets store test fixture"),
    "LOG_LEVEL": ("info", "SQL logging level read"),
    "OPENAI_API_KEY": ("sk-changeme", "OpenAI provider key (AI doctor)"),
    "OTEL_EXPORTER_OTLP_ENDPOINT": (
        "http://localhost:4318",
        "OpenTelemetry collector endpoint",
    ),
    "PLAYWRIGHT_SNAPSHOT": ("", "set to 1 to update admin e2e snapshots"),
    "RABBITMQ_URL": (
        "amqp://guest:guest@localhost:5672//",
        "queue doctor RabbitMQ URL",
    ),
    "REALTIME_PORT": ("7071", "demos/realtime-monitor port"),
    "REDIS_URL": ("redis://localhost:6379/0", "queue doctor Redis URL"),
    "SENTRY_DSN": (
        "",
        (
            "Sentry DSN; error tracking falls back to this when "
            "LEX_MONITOR__ERROR_TRACKING__DSN is unset"
        ),
    ),
    "SMTP_HOST": ("localhost:25", "notification doctor SMTP host"),
    "TEST_POSTGRES_DSN": (
        "postgresql://lexigram:lexigram@localhost:5432/lexigram_test",
        "events/tasks postgres integration tests",
    ),
    "VECTOR_BACKEND": ("memory", "vector doctor backend name"),
    "VECTOR_STORE_BACKEND": ("memory", "vector doctor backend name"),
}

# Comment block emitted above SUPPLEMENTAL_VARS, grouped by what needs them.
SUPPLEMENTAL_HEADER = [
    "# ---------------------------------------------------------------------------",
    "# Variables referenced directly in source (os.getenv / os.environ) — optional;",
    "# unset values fall back to code defaults. Keep in sync with source usage.",
    "#",
    "# Required by other demos:",
    "#   LEXIGRAM_EXPERIMENT_SEED (llm-experiment), REALTIME_PORT (realtime-monitor)",
    "# Referenced by core framework source / doctor CLIs:",
    "#   ANTHROPIC_API_KEY, APNS_KEY_PATH, APP_ENV, AUDIT_HMAC_KEY, AUTH_JWT_SECRET,",
    "#   BROKER_URL, DATABASE_URL, F5_TTS_REFERENCE_ROOT, FCM_SERVER_KEY, JWT_SECRET,",
    "#   OAUTH_CLIENT_SECRET, OPENAI_API_KEY, OTEL_EXPORTER_OTLP_ENDPOINT,",
    "#   RABBITMQ_URL, REDIS_URL, SMTP_HOST, VECTOR_BACKEND, VECTOR_STORE_BACKEND",
    "# Test/tooling only:",
    "#   ADMIN_BASE, ADMIN_SETUP_TOKEN, AUTH_SECRET, ENVIRONMENT, LEXI_SECRET,",
    "#   LOG_LEVEL, PLAYWRIGHT_SNAPSHOT, TEST_POSTGRES_DSN",
    "# ---------------------------------------------------------------------------",
]


def generate() -> None:
    """Write .env.full.example from the env var catalog."""
    sections = parse(CATALOG)
    lines = [
        "# Lexigram Framework full environment configuration example.",
        "#",
        "# Copy to .env and adjust values for your deployment:",
        "#   cp .env.full.example .env",
        "#",
        "# Generated from docs/reference/REF_ENV_VARS.md by",
        "# dev/generators/env_example.py — do not edit by hand.",
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
        for name, typ, catalog_default, desc in rows:
            default = SERVICE_DEFAULTS.get(name)
            if default:
                val = default
            elif name.endswith(SECRET_SUFFIX) or "SECRET" in name or "API_KEY" in name:
                val = "<change-me-in-production>"
            else:
                val = _resolve_default(catalog_default)
            comment = f"  # {typ}" if typ else ""
            if desc:
                comment = f"  # {desc} ({typ})" if typ else f"  # {desc}"
            lines.append(f"{name}={val}{comment}")

    lines.append("")
    lines.extend(SUPPLEMENTAL_HEADER)
    for name, (value, comment) in SUPPLEMENTAL_VARS.items():
        suffix = f"  # {comment}" if comment else ""
        lines.append(f"{name}={value}{suffix}")

    OUT.write_text("\n".join(lines) + "\n")
    print(
        f"wrote {OUT} with {len(sections)} package sections, {sum(len(r) for _, r in sections)} vars"
    )


if __name__ == "__main__":
    generate()
