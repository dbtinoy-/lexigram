# YAML Config Example Generator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a generator for `application.example.yaml` and fill in all missing package sections, so the YAML example is complete, accurate, and auto-regenerable from the env var catalog.

**Architecture:** Write `dev/generators/yaml_config_example.py` that parses `docs/reference/REF_ENV_VARS.md`, converts env var paths to nested YAML keys, and emits a complete config example. Then manually add the 10 missing package sections + core section to the existing YAML, and verify the generator reproduces them.

**Tech Stack:** Python 3.11+, re, yaml (PyYAML for validation), pathlib. Same pattern as `dev/generators/env_example.py`.

**Spec:** This plan. Research source: `dev/generators/env_example.py`, `docs/reference/REF_ENV_VARS.md`, `application.example.yaml`, and config classes across 10 missing packages.

---

## Background

- `application.example.yaml` (1687 lines) is manually maintained — no generator exists
- `docs/reference/REF_ENV_VARS.md` has 1079 vars across 43 packages — the YAML covers 37
- 10 packages are missing from the YAML entirely; 1 package (`lexigram-notification`) has partial coverage
- The YAML header claims values are "exact defaults from each package's config class" — this is mostly true for existing sections but cannot be verified for missing ones

## Env Var → YAML Key Mapping

```
Env var:  LEX_AUTH__TOKEN__ALGORITHM
Prefix:   LEX_
Strip:    AUTH__TOKEN__ALGORITHM
Lower:    auth__token__algorithm
Split:    ["auth", "token", "algorithm"]
YAML key: auth.token.algorithm
```

---

## Global Constraints

- Follow repo conventions from `AGENTS.md` (absolute imports, Google docstrings, ruff clean)
- Generator must be standalone-runnable: `uv run python dev/generators/yaml_config_example.py`
- Output must be valid YAML (validate with `yaml.safe_load()`)
- Match existing YAML style: `# env_prefix:` headers, `# ──` section separators, `${VAR}` for secrets
- Do not create worktrees or branches unless asked

---

### Task 1: Create the YAML config example generator skeleton

**Files:**
- Create: `dev/generators/yaml_config_example.py`

**Interfaces:**
- Consumes: `docs/reference/REF_ENV_VARS.md` (same catalog as `env_example.py`)
- Produces: `application.example.yaml` (overwrites existing file)

- [ ] **Step 1: Create the generator file with imports and constants**

```python
#!/usr/bin/env python3
"""Generate application.example.yaml from docs/reference/REF_ENV_VARS.md.

Usage:
    uv run python dev/generators/yaml_config_example.py
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml  # noqa: F401 — used for validation only

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/reference/REF_ENV_VARS.md"
OUT = ROOT / "application.example.yaml"

PKG_HEADER = re.compile(r"^### `([^`]+)` \((\d+) vars\)$")
ROW = re.compile(r"^`([A-Z][A-Z0-9_]*)`$")
```

- [ ] **Step 2: Copy `_split_cells()` and `_resolve_default()` from `env_example.py`**

These are identical to the env_example helpers. Import from `env_example` or duplicate (since generators run standalone). Preference: import from env_example since they're in the same directory.

```python
from dev.generators.env_example import _split_cells, _resolve_default, parse
```

If import path doesn't work standalone, duplicate the ~30 lines.

- [ ] **Step 3: Run and verify import path works**

```bash
uv run python -c "from dev.generators.env_example import parse; print('OK')"
```

Expected: prints `OK`

---

### Task 2: Implement YAML key derivation and nesting logic

**Files:**
- Create: `dev/generators/yaml_config_example.py` (append to Task 1 file)

**Interfaces:**
- Consumes: list of `(env_var_name, type, default, description)` tuples per package
- Produces: nested dict structure suitable for YAML serialization

- [ ] **Step 1: Implement `env_var_to_yaml_path()`**

```python
# Packages where env_prefix is NOT "LEX_<SECTION>__" — need explicit mapping.
# Key = first lowercase segment after stripping LEX_, Value = YAML section key.
# Only entries that differ from the default (first segment = YAML key) need listing.
_PACKAGE_TO_YAML_SECTION: dict[str, str] = {
    "lexigram": "",  # core — folded into root
    "auth": "auth",
    "cache": "cache",
    "web": "web",
    "sql": "db",
    "events": "events",
    "graphql": "graphql",
    "monitor": "monitor",
    "search": "search",
    "storage": "storage",
    "vector": "vector",
    "nosql": "nosql",
    "graph": "graph",
    "tasks": "tasks",
    "features": "features",
    "resilience": "resilience",
    "admin": "admin",
    "ai": "ai",
    "ai_rag": "ai_rag",
    "ai_memory": "ai_memory",
    "ai_session": "ai_session",
    "ai_agents": "ai_agents",
    "ai_governance": "ai_governance",
    "ai_guard": "ai_guard",
    "ai_feedback": "ai_feedback",
    "ai_prompt": "ai_prompt",
    "ai_skills": "ai_skills",
    "ai_workers": "ai_workers",
    "ai_mcp": "ai_mcp",
    "ai_observability": "ai_observability",
    "ai_evaluation": "ai_evaluation",
    "ai_llm": "ai_llm",
    "audit": "audit",
    "http": "http",
    "secrets": "secrets",
    "tenancy": "tenancy",
    "webhook": "webhook",
    "multimedia": "multimedia",
    "ui": "ui",
    "cli": "cli",
    "notification": "notification",
    "testing": "testing",
    "middleware": "middleware",
    "security": "security",
    "idempotency": "idempotency",
    "mapping": "mapping",
    "workflow": "workflow",
}


def env_var_to_yaml_path(env_var: str, pkg_key: str) -> list[str] | None:
    """Convert an env var name to a YAML key path.

    Args:
        env_var: Full env var name, e.g. ``LEX_AUTH__TOKEN__ALGORITHM``.
        pkg_key: Package name from catalog header, e.g. ``lexigram-auth``.

    Returns:
        List of YAML key segments, or None if the var should be skipped
        (e.g. env vars not in the LEX_ namespace).
    """
    if not env_var.startswith("LEX_"):
        return None
    # Strip LEX_ prefix
    rest = env_var[4:]  # AUTH__TOKEN__ALGORITHM
    # Split on __
    segments = rest.lower().split("__")
    # First segment is the package area
    first = segments[0]
    yaml_section = _PACKAGE_TO_YAML_SECTION.get(first, first)
    if not yaml_section:
        return None  # core vars folded into root — skip
    # Remaining segments are nested keys
    return [yaml_section] + segments[1:]
```

- [ ] **Step 2: Implement `build_yaml_tree()`**

```python
def build_yaml_tree(
    sections: list[tuple[str, list[tuple[str, str, str, str]]]],
) -> dict:
    """Build a nested dict from parsed catalog sections.

    Args:
        sections: List of (pkg_name, [(env_var, type, default, desc)]) tuples.

    Returns:
        Nested dict suitable for yaml.dump().
    """
    tree: dict = {}
    for pkg_name, rows in sections:
        for env_var, typ, default, desc in rows:
            path = env_var_to_yaml_path(env_var, pkg_name)
            if not path:
                continue
            # Navigate/create nested dict
            node = tree
            for key in path[:-1]:
                node = node.setdefault(key, {})
            # Resolve value
            value = _resolve_default(default)
            # Secrets get placeholder
            if _is_secret(env_var):
                value = "${" + env_var + "}"
            elif not value:
                value = None
            else:
                value = _coerce_yaml_value(value, typ)
            node[path[-1]] = value
    return tree
```

- [ ] **Step 3: Implement `_is_secret()` and `_coerce_yaml_value()`**

```python
_SECRET_SUFFIXES = (
    "SECRET", "SECRET_KEY", "API_KEY", "PASSWORD",
    "TOKEN", "HMAC_KEY", "CREDENTIALS", "PRIVATE_KEY",
)


def _is_secret(env_var: str) -> bool:
    """Check if an env var name suggests it holds a secret."""
    return env_var.endswith(_SECRET_SUFFIXES) or "SECRET" in env_var or "API_KEY" in env_var


def _coerce_yaml_value(raw: str, typ: str) -> str | int | float | bool | None:
    """Convert a string default to the appropriate Python/YAML type."""
    if raw in ("", "—", "(complex)", "None"):
        return None
    # Boolean
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    # Integer
    try:
        return int(raw)
    except ValueError:
        pass
    # Float
    try:
        return float(raw)
    except ValueError:
        pass
    return raw
```

- [ ] **Step 4: Test the nesting logic in isolation**

```python
# Quick smoke test — add at bottom, run, then remove
if __name__ == "__main__":
    from dev.generators.env_example import parse
    sections = parse(CATALOG)
    tree = build_yaml_tree(sections)
    print(yaml.dump(tree, default_flow_style=False, sort_keys=True)[:500])
```

Run: `uv run python dev/generators/yaml_config_example.py`
Expected: prints a partial YAML tree with correct nesting

---

### Task 3: Implement YAML output with comments and formatting

**Files:**
- Create: `dev/generators/yaml_config_example.py` (append to Task 2 file)

**Interfaces:**
- Consumes: parsed catalog sections
- Produces: formatted `application.example.yaml` with headers, comments, and `${VAR}` placeholders

- [ ] **Step 1: Implement `generate()` with section-by-section output**

The YAML file cannot use PyYAML's `yaml.dump()` directly because it needs:
- `# env_prefix:` comments per section
- `${VAR}` placeholder syntax (not valid YAML values)
- Commented-out multi-backend examples
- Alignment and formatting

Strategy: emit YAML line-by-line, building each section from the catalog.

```python
# Package metadata: keyed by catalog pkg_name (e.g. "lexigram-sql", "lexigram-auth").
# Value = (display_name, env_prefix_override_or_None)
_SECTION_META: dict[str, tuple[str, str | None]] = {
    "lexigram": ("Core Framework", None),
    "lexigram-sql": ("SQL Database", "LEX_SQL__"),
    "lexigram-cache": ("Cache", "LEX_CACHE__"),
    "lexigram-web": ("Web", "LEX_WEB__"),
    "lexigram-auth": ("Auth", "LEX_AUTH__"),
    "lexigram-events": ("Events", "LEX_EVENTS__"),
    "lexigram-graphql": ("GraphQL", "LEX_GRAPHQL__"),
    "lexigram-monitor": ("Monitor", "LEX_MONITOR__"),
    "lexigram-search": ("Search", "LEX_SEARCH__"),
    "lexigram-storage": ("Storage", "LEX_STORAGE__"),
    "lexigram-vector": ("Vector", "LEX_VECTOR__"),
    "lexigram-nosql": ("NoSQL", "LEX_NOSQL__"),
    "lexigram-graph": ("Graph", "LEX_GRAPH__"),
    "lexigram-tasks": ("Tasks", "LEX_TASKS__"),
    "lexigram-features": ("Features", "LEX_FEATURES__"),
    "lexigram-resilience": ("Resilience", "LEX_RESILIENCE__"),
    "lexigram-admin": ("Admin", "LEX_ADMIN__"),
    "lexigram-ai": ("AI", "LEX_AI__"),
    "lexigram-ai-rag": ("AI RAG", "LEX_AI_RAG__"),
    "lexigram-ai-memory": ("AI Memory", "LEX_AI_MEMORY__"),
    "lexigram-ai-session": ("AI Session", "LEX_AI_SESSION__"),
    "lexigram-ai-agents": ("AI Agents", "LEX_AI_AGENTS__"),
    "lexigram-ai-governance": ("AI Governance", "LEX_AI_GOVERNANCE__"),
    "lexigram-ai-guard": ("AI Guard", "LEX_AI_GUARD__"),
    "lexigram-ai-feedback": ("AI Feedback", "LEX_AI_FEEDBACK__"),
    "lexigram-ai-prompt": ("AI Prompt", "LEX_AI_PROMPT__"),
    "lexigram-ai-skills": ("AI Skills", "LEX_AI_SKILLS__"),
    "lexigram-ai-workers": ("AI Workers", "LEX_AI_WORKERS__"),
    "lexigram-ai-mcp": ("AI MCP", "LEX_AI_MCP__"),
    "lexigram-ai-observability": ("AI Observability", "LEX_AI_OBSERVABILITY__"),
    "lexigram-ai-evaluation": ("AI Evaluation", "LEX_AI_EVALUATION__"),
    "lexigram-ai-llm": ("AI LLM", "LEX_AI_LLM__"),
    "lexigram-audit": ("Audit", "LEX_AUDIT__"),
    "lexigram-http": ("HTTP Client", "LEX_HTTP__"),
    "lexigram-secrets": ("Secrets", "LEX_SECRETS_"),
    "lexigram-tenancy": ("Tenancy", "LEX_TENANCY__"),
    "lexigram-webhook": ("Webhook", "LEX_WEBHOOK__"),
    "lexigram-multimedia": ("Multimedia", None),
    "lexigram-ui": ("UI", "LEX_UI__"),
    "lexigram-cli": ("CLI", None),
    "lexigram-notification": ("Notification", "LEX_NOTIFICATION__"),
    "lexigram-testing": ("Testing", "LEX_TESTING__"),
    "lexigram-middleware": ("Middleware", "LEX_MIDDLEWARE__"),
    "lexigram-security": ("Security", "LEX_SECURITY__"),
    "lexigram-idempotency": ("Idempotency", "LEX_IDEMPOTENCY__"),
    "lexigram-mapping": ("Mapping", "LEX_MAPPING__"),
    "lexigram-workflow": ("Workflow", "LEX_WORKFLOW__"),
}


def generate() -> None:
    """Write application.example.yaml from the env var catalog."""
    sections = parse(CATALOG)

    # Build per-package variable groups
    pkg_vars: dict[str, list[tuple[str, str, str, str]]] = {}
    for pkg_name, rows in sections:
        pkg_vars[pkg_name] = rows

    lines = _emit_header()

    # Emit each package section
    for pkg_name in sorted(pkg_vars.keys()):
        rows = pkg_vars[pkg_name]
        if not rows:
            continue
        # Determine YAML section key from first var's path
        first_var = rows[0][0]
        path = env_var_to_yaml_path(first_var, pkg_name)
        if not path:
            continue  # core — skip
        yaml_section = path[0]
        display_name, prefix_override = _SECTION_META.get(pkg_name, (yaml_section, None))
        env_prefix = prefix_override or _derive_env_prefix(rows[0][0])

        lines.append("")
        sep_len = max(1, 70 - len(display_name) - len(pkg_name))
        lines.append(f"# ── {display_name} ({pkg_name}) ──" + "─" * sep_len)
        lines.append(f"# env_prefix: {env_prefix}")
        lines.append(f"{yaml_section}:")

        # Group vars by nesting depth
        nested = _group_by_nesting(rows, yaml_section)
        _emit_section(lines, nested, indent=2)

    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT} ({len(lines)} lines)")


def _emit_header() -> list[str]:
    return [
        "# ==============================================================================",
        "# application.example.yaml",
        "# Lexigram Framework — complete configuration reference.",
        "#",
        "# All values shown are exact defaults taken from each package's config class.",
        "# Secrets:  prefer environment variables or a vault over plaintext.",
        '#           Syntax: "${ENV_VAR_NAME}" lets the loader substitute at runtime.',
        "# Env-var overrides use double-underscore nesting, e.g.:",
        "#   LEX_WEB__SERVER__PORT=9000  →  web.server.port = 9000",
        "# ==============================================================================",
    ]
```

- [ ] **Step 2: Implement `_group_by_nesting()` and `_emit_section()`**

```python
def _derive_env_prefix(env_var: str) -> str:
    """Derive the env_prefix from the first env var."""
    if not env_var.startswith("LEX_"):
        return "LEX_"
    # LEX_AUTH__TOKEN__ALGORITHM → strip last 2 segments → LEX_AUTH__
    parts = env_var[4:].split("__")
    return "LEX_" + parts[0] + "__"


def _group_by_nesting(
    rows: list[tuple[str, str, str, str]], yaml_section: str
) -> dict:
    """Group catalog rows into a nested dict keyed by YAML path segments."""
    tree: dict = {}
    for env_var, typ, default, desc in rows:
        path = env_var_to_yaml_path(env_var, "unused")
        if not path or len(path) < 2:
            continue
        # path = [yaml_section, key1, key2, ...]
        node = tree
        for seg in path[1:-1]:
            node = node.setdefault(seg, {})
        # Leaf
        value = _resolve_default(default)
        if _is_secret(env_var):
            value = "${" + env_var + "}"
        elif not value:
            value = None
        else:
            value = _coerce_yaml_value(value, typ)
        node[path[-1]] = {"_value": value, "_desc": desc, "_type": typ}
    return tree


def _emit_section(lines: list[str], tree: dict, indent: int) -> None:
    """Recursively emit a YAML section with proper indentation."""
    prefix = " " * indent
    for key in sorted(tree.keys()):
        node = tree[key]
        if isinstance(node, dict) and "_value" in node:
            # Leaf
            value = node["_value"]
            desc = node["_desc"]
            val_str = _format_yaml_value(value)
            comment = f"  # {desc}" if desc else ""
            lines.append(f"{prefix}{key}: {val_str}{comment}")
        else:
            # Nested dict
            lines.append(f"{prefix}{key}:")
            _emit_section(lines, node, indent + 2)


def _format_yaml_value(value) -> str:
    """Format a Python value for YAML output."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        # Quote strings that could be misinterpreted
        if value.startswith("${"):
            return f'"{value}"'
        if value.lower() in ("true", "false", "null", "yes", "no"):
            return f'"{value}"'
        return f'"{value}"'
    return str(value)
```

- [ ] **Step 3: Run the generator and validate output**

```bash
uv run python dev/generators/yaml_config_example.py
uv run python -c "import yaml; yaml.safe_load(open('application.example.yaml')); print('valid YAML')"
```

Expected: prints `wrote application.example.yaml (N lines)` then `valid YAML`

---

### Task 4: Add missing package sections to the YAML manually

The generator from Tasks 1-3 produces a flat catalog-derived YAML. The existing hand-crafted YAML has richer formatting (commented-out multi-backend examples, alignment, descriptive comments). Rather than replace the entire file with the generator output, manually add the 10 missing sections to the existing file first, then tune the generator to match.

**Files:**
- Modify: `application.example.yaml` (append new sections before the `testing:` section)

**Section insertion point:** Before `# ── Testing Utilities` (line 1681)

- [ ] **Step 1: Add `lexigram` (core) section**

Insert before the SQL section (after the header):

```yaml
# ── Core Framework (lexigram) ──────────────────────────────────────────────────
# env_prefix: LEX_LEXIGRAM__  |  config_section: root (folded)
# Core config fields live at the root level of the YAML.
# The lexigram: section is folded into root-level fields by LexigramConfig.
app_name: "lexigram-app"
debug: false
env: development
logging:
  level: info
  format: json
  structlog processors:
    - add_timestamp
    - add_log_level
    - stack_info_merge
    - exception_renderer
modules: []
discovery:
  auto_discover: true
  package_patterns:
    - "lexigram_*"
health:
  enabled: true
  path: /health
  detailed: false
```

- [ ] **Step 2: Add `lexigram-ai-evaluation` section**

```yaml
# ── AI Evaluation (lexigram-ai-evaluation) ─────────────────────────────────────
# env_prefix: LEX_AI_EVALUATION__
ai_evaluation:
  enabled: true
  experiment_dir: null
  default_seed: null
  default_threshold: 0.8
  embedding_model: "text-embedding-3-small"
  include_metadata: true
  max_samples: null
  max_retries: 3
  timeout_seconds: 30
```

- [ ] **Step 3: Add `lexigram-audit` section**

```yaml
# ── Audit (lexigram-audit) ──────────────────────────────────────────────────────
# env_prefix: LEX_AUDIT__
audit:
  store_backend: sql
  table_name: audit_log
  hmac_key: null
  retention_policy:
    name: default
    default_retention_days: 365
    severity_overrides:
      critical: 2555
      high: 1095
  verification_schedule: "0 * * * *"
  verification_batch_size: 100
  enable_admin: true
```

- [ ] **Step 4: Add `lexigram-http` section**

```yaml
# ── HTTP Client (lexigram-http) ─────────────────────────────────────────────────
# env_prefix: LEX_HTTP__
http:
  pool:
    max_connections: 10
    max_keepalive_connections: 5
    max_connections_per_host: 10
    timeout: 30.0
    ttl_dns_cache: 300
    force_close: false
  proxy: null
  trust_env: true
  cookie_jar: true
  enforce_url_safety: true
  max_redirects: 5
```

- [ ] **Step 5: Add `lexigram-secrets` section**

```yaml
# ── Secrets (lexigram-secrets) ──────────────────────────────────────────────────
# env_prefix: LEX_SECRETS_
secrets:
  name: secrets
  enabled: true
  backend_type: memory
  backend_options: {}
  max_age_seconds: 7776000.0
  warning_before_seconds: 86400.0
  tenant_id: null
  audit_actor_id: secrets-system
```

- [ ] **Step 6: Add `lexigram-tenancy` section**

```yaml
# ── Tenancy (lexigram-tenancy) ──────────────────────────────────────────────────
# env_prefix: LEX_TENANCY__
tenancy:
  resolution:
    resolvers:
      - jwt_claim
      - header
      - subdomain
      - path
    header_name: x-tenant-id
    subdomain_pattern: null
    path_pattern: "/tenants/{tenant_id}/"
    jwt_claim_key: tenant_id
    validator_cache_ttl: 300
    trusted_resolvers:
      - jwt_claim
    strict_membership: true
  lifecycle:
    isolation_strategy: row_level
    auto_provision_isolation: true
  overrides:
    cache_ttl: 60
  integration:
    cache_key_prefix: true
    sql_context_bridge: true
```

- [ ] **Step 7: Add `lexigram-webhook` section**

```yaml
# ── Webhook (lexigram-webhook) ──────────────────────────────────────────────────
# env_prefix: LEX_WEBHOOK__
webhook:
  store_backend: memory
  allow_private_urls: false
  retry_max_attempts: 5
  retry_base_delay: 1.0
  retry_max_delay: 60.0
  retry_backoff_factor: 2.0
  secret_length: 32
  secret_rotation_grace_hours: 24
  delivery_timeout_seconds: 30.0
  disable_after_consecutive_failures: 50
  failure_window_hours: 24
  signature_algorithm: sha256
  enable_admin: true
  delivery_log_retention_days: 30
  signature_header: "X-Webhook-Signature"
  event_type_header: "X-Webhook-Event-Type"
  event_id_header: "X-Webhook-Event-ID"
  timestamp_header: "X-Webhook-Timestamp"
```

- [ ] **Step 8: Add `lexigram-multimedia` section**

```yaml
# ── Multimedia (lexigram-multimedia) ────────────────────────────────────────────
# env_prefix: LEX_MULTIMEDIA__  (experimental — not loaded in production by default)
multimedia:
  storage_path_prefix: "multimedia/"
  cache_results: false
  tts:
    backend: local-http
    local_http_base_url: "http://localhost:5002"
    timeout: 60.0
  music:
    backend: local-http
    local_http_base_url: "http://localhost:5003"
    timeout: 60.0
  video:
    backend: local-http
    local_http_base_url: "http://localhost:5004"
    timeout: null
    processing:
      ffmpeg_binary: ffmpeg
      max_concurrent_jobs: 2
      temp_dir: null
      timeout: 300.0
      max_asset_bytes: 26214400
  image:
    backend: local-http
    local_http_base_url: "http://localhost:5005"
    timeout: 60.0
  upscale:
    backend: real-esrgan
    real_esrgan_base_url: "http://localhost:5400"
    hat_base_url: "http://localhost:5401"
    timeout: 30.0
  interpolate:
    backend: rife
    rife_base_url: "http://localhost:5500"
    timeout: 15.0
  beat:
    backend: librosa
    librosa_sample_rate: 22050
    max_asset_bytes: 26214400
    max_analyze_samples: 60000000
    madmom_base_url: "http://localhost:5600"
    timeout: 30.0
```

- [ ] **Step 9: Add `lexigram-ui` section**

```yaml
# ── UI (lexigram-ui) ────────────────────────────────────────────────────────────
# env_prefix: LEX_UI__  (experimental — HTMX component library)
ui:
  default_theme: default
  auto_escape: true
  htmx_version: "2.0.4"
  debug_components: false
  theme: light
  enable_sse: false
  enable_realtime: false
```

- [ ] **Step 10: Add missing fields to `lexigram-notification` section**

The existing `notification:` and `mailer:` sections are incomplete. Add missing fields:

```yaml
# ── Notification (lexigram-notification) ────────────────────────────────────────
# env_prefix: LEX_NOTIFICATION__
# (existing notification: section — add inbox subsection)
notification:
  # ... existing sms_backends, push_backends ...

# Add to the existing mailer section:
# mailer:
#   # ... existing backends ...
#   console_fallback: true
#   retry_max_attempts: 0
#   retry_base_delay: 60.0

# Add new inbox section:
inbox:
  store_backend: database
  max_page_size: 50
  retention_days: 30
  mark_read_on_fetch: false
```

- [ ] **Step 11: Validate the updated YAML**

```bash
uv run python -c "import yaml; yaml.safe_load(open('application.example.yaml')); print('valid YAML')"
wc -l application.example.yaml
```

Expected: `valid YAML`, line count > 1687

---

### Task 5: Tune the generator to reproduce the manual sections

**Files:**
- Modify: `dev/generators/yaml_config_example.py`

**Interfaces:**
- Consumes: catalog + manual section metadata
- Produces: `application.example.yaml` matching the hand-crafted version

- [ ] **Step 1: Add `_MANUAL_SECTIONS` for non-catalog vars**

Some YAML sections have vars not in the catalog (e.g., core `app_name`, `debug`, `env`). These are hardcoded in the generator:

```python
# Sections with vars not in the catalog (core config, etc.)
_MANUAL_SECTIONS: dict[str, str] = {
    "": """# Core config fields live at the root level of the YAML.
# The lexigram: section is folded into root-level fields by LexigramConfig.
app_name: "lexigram-app"
debug: false
env: development
logging:
  level: info
  format: json
modules: []
discovery:
  auto_discover: true
health:
  enabled: true
  path: /health
  detailed: false""",
}
```

- [ ] **Step 2: Run the generator against the existing file**

```bash
uv run python dev/generators/yaml_config_example.py
diff <(cat application.example.yaml) /tmp/expected.yaml  # compare
```

- [ ] **Step 3: Wire `_MANUAL_SECTIONS` into `generate()`**

The `generate()` function must emit `_MANUAL_SECTIONS` content (e.g., core config) before the catalog-derived sections:

```python
def generate() -> None:
    sections = parse(CATALOG)
    lines = _emit_header()

    # Emit manual sections first (core config, etc.)
    for key, content in _MANUAL_SECTIONS.items():
        lines.append("")
        lines.append(content)

    # Then emit catalog-derived sections
    # ... (existing logic)
```

- [ ] **Step 4: Fix discrepancies and iterate**

The generator output will differ from the hand-crafted file in:
- Commented-out multi-backend examples (Redis, Memcached, etc.)
- `${VAR}` placeholder usage
- Section ordering
- Descriptive inline comments

For the first pass, accept that the generator produces a simpler output. The hand-crafted file is the source of truth for formatting; the generator is for completeness/accuracy.

- [ ] **Step 4: Add a CI check (optional, low priority)**

Add a `dev/checks/yaml_config_coverage.py` that verifies all packages in the catalog have a corresponding section in `application.example.yaml`. This catches future drift.

---

### Task 6: Run lint, format, and verify

**Files:**
- `dev/generators/yaml_config_example.py`
- `application.example.yaml`

- [ ] **Step 1: Lint and format the generator**

```bash
uv run ruff check dev/generators/yaml_config_example.py
uv run ruff format dev/generators/yaml_config_example.py
```

Expected: no errors, no format changes

- [ ] **Step 2: Validate the generated YAML parses correctly**

```bash
uv run python -c "
import yaml
from pathlib import Path
content = Path('application.example.yaml').read_text()
data = yaml.safe_load(content)
print(f'parsed {len(data)} top-level keys')
print('sections:', sorted(data.keys()))
"
```

Expected: prints ~45 top-level keys

- [ ] **Step 3: Compare catalog coverage**

```bash
uv run python -c "
import re
from pathlib import Path

catalog = Path('docs/reference/REF_ENV_VARS.md').read_text()
yaml_content = Path('application.example.yaml').read_text()

# Packages in catalog
pkgs_in_catalog = set(re.findall(r'^### \`([^`]+)\`', catalog, re.MULTILINE))

# Packages referenced in YAML
pkgs_in_yaml = set(re.findall(r'\((lexigram[^)]+)\)', yaml_content))

missing = pkgs_in_catalog - pkgs_in_yaml
print(f'catalog: {len(pkgs_in_catalog)} packages')
print(f'yaml: {len(pkgs_in_yaml)} packages')
print(f'missing from yaml: {sorted(missing) if missing else \"none\"}')
"
```

Expected: `missing from yaml: none`

---

## Verification Checklist

After all tasks:

1. `application.example.yaml` is valid YAML (parses without error)
2. All 43 catalog packages have a corresponding section (or are marked N/A like `lexigram-cli`)
3. `dev/generators/yaml_config_example.py` is runnable standalone
4. `uv run ruff check dev/generators/yaml_config_example.py` passes
5. `uv run ruff format --check dev/generators/yaml_config_example.py` passes
6. The generator output covers all catalog packages (may differ in formatting from hand-crafted file)
