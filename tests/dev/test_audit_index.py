from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lexigram.serialization.backends import json as json_backend
from dev.audit.index import (
    build_audit_index,
    render_index_json,
    render_index_markdown,
)
from dev.core.registry import GeneratorRegistry


@dataclass(frozen=True, slots=True)
class _FakeGenerator:
    name: str
    description: str
    output_file: str


def _write_sample_workspace(root: Path) -> None:
    (root / "pyproject.toml").write_text('[project]\nname = "workspace"\n', encoding="utf-8")
    package_root = root / "lexigram"
    package_root.mkdir()
    (package_root / "pyproject.toml").write_text(
        '[project]\nname = "lexigram"\n',
        encoding="utf-8",
    )
    config_dir = package_root / "src" / "lexigram"
    config_dir.mkdir(parents=True)
    (config_dir / "config.py").write_text(
        """
from __future__ import annotations

from typing import ClassVar

from pydantic import ConfigDict, Field


class NestedConfig:
    enabled: bool = True


class AppConfig:
    model_config: ClassVar[ConfigDict] = ConfigDict(
        env_prefix=\"LEX_APP__\",
        env_nested_delimiter=\"__\",
    )
    debug: bool = Field(default=False, description=\"Enable debug mode.\")
    nested: NestedConfig = NestedConfig()
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_audit_index_includes_tool_health_rules_and_package_coverage(tmp_path: Path) -> None:
    _write_sample_workspace(tmp_path)
    (tmp_path / "AUDIT_ENV_VARS.md").write_text(
        """
# AUDIT_ENV_VARS.md

| Key | Status |
|-----|--------|
| demo | correct |
| missing | suspect |
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "AUDIT_QUALITY.md").write_text(
        """
# AUDIT_QUALITY.md

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **PASS** | 0 | 10 ms | `uv run ruff check .` |
| `Mypy` | **FAIL** | 1 | 22 ms | `uv run mypy lexigram/src/` |
| `Pytest` | **PASS** | 0 | 33 ms | `uv run pytest tests/scripts -q --no-cov` |
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "AUDIT_RULES.md").write_text(
        """
# AUDIT_RULES.md

## Severity Summary

| Severity | Count |
|----------|-------|
| critical | 2 |
| important | 4 |
| minor | 1 |

## Findings

| File | Line | Rule ID | Severity | Message |
|------|------|---------|----------|---------|
| `lexigram-admin/src/example.py` | 10 | `no-cross-extension-import` | `critical` | first critical drift |
| `lexigram-web/src/example.py` | 20 | `init-no-logic` | `important` | init logic drift |
| `lexigram-web/src/other.py` | 30 | `import-absolute-only` | `important` | import drift |

## Package Coverage

- Discovered packages: 3
- Covered packages: 2
- Missing packages: 1
- Coverage status: **FAIL**

### Missing Packages

- `lexigram-vector`
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "AUDIT_TESTS.md").write_text(
        """
# AUDIT_TESTS.md

## Execution Evidence

| Label | Scope | Command | Exit Code | Duration | Parsed Summary | Example Failures |
|-------|-------|---------|-----------|----------|----------------|------------------|
| Scripts audit smoke | `tests/scripts` | `uv run pytest tests/scripts -q --no-cov` | 0 | 11 ms | `2 passed in 0.11s` | none |
| Package smoke sample | `lexigram/tests` | `uv run pytest lexigram/tests -q --no-cov` | 1 | 22 ms | `1 failed in 0.22s` | `lexigram/tests/test_sample.py::test_sample` |
""".strip()
        + "\n",
        encoding="utf-8",
    )

    registry = GeneratorRegistry[_FakeGenerator]()
    for generator in (
        _FakeGenerator("env_vars", "Environment variables", "AUDIT_ENV_VARS.md"),
        _FakeGenerator("quality", "Quality tools", "AUDIT_QUALITY.md"),
        _FakeGenerator("rules", "Rules audit", "AUDIT_RULES.md"),
        _FakeGenerator("tests", "Tests audit", "AUDIT_TESTS.md"),
        _FakeGenerator("index", "Index audit", "AUDIT_INDEX.md"),
    ):
        registry.register(generator.name, generator)

    snapshot = build_audit_index(tmp_path, registry, self_name="index")
    markdown = render_index_markdown(
        snapshot,
        output_markdown="AUDIT_INDEX.md",
        output_json="AUDIT_INDEX.json",
    )
    payload = json_backend.loads_str(
        render_index_json(
            snapshot,
            output_markdown="AUDIT_INDEX.md",
            output_json="AUDIT_INDEX.json",
        )
    )

    assert "## Tool Health" in markdown
    assert "| `ruff` | PASS | `quality` |" in markdown
    assert "| `mypy` | FAIL | `quality` |" in markdown
    assert "| `pytest` | FAIL | `tests` |" in markdown
    assert "## Rules Health" in markdown
    assert "- Critical violations: 2" in markdown
    assert "- Important violations: 4" in markdown
    assert "no-cross-extension-import" in markdown
    assert "import-absolute-only" in markdown
    assert "## Package Coverage" in markdown
    assert "`lexigram-vector`" in markdown
    assert payload["tool_health"]["ruff"]["status"] == "PASS"
    assert payload["tool_health"]["mypy"]["status"] == "FAIL"
    assert payload["tool_health"]["pytest"]["status"] == "FAIL"
    assert payload["rules_summary"]["critical"] == 2
    assert payload["rules_summary"]["important"] == 4
    assert payload["rules_summary"]["top_misalignments"][0]["rule_id"] == "import-absolute-only"
    assert payload["package_coverage"]["missing_packages"] == ["lexigram-vector"]
    assert payload["reports"]
    assert any(report["report_path"] == "AUDIT_ENV_VARS.md" for report in payload["reports"])
