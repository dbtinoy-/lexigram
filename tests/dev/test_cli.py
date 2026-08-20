from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dev.audit.generators import build_audit_registry
from dev.audit.generators.base import AuditRunResult
from dev.cli import main
from dev.core.registry import GeneratorRegistry


@dataclass(frozen=True, slots=True)
class _FakeAuditGenerator:
    name: str
    description: str
    output_file: str
    env_vars: tuple[str, ...] = ()

    def validate(self, *, root: Path | None = None) -> AuditRunResult:
        return AuditRunResult(
            name=self.name,
            success=True,
            message=f"ready for {root}",
        )

    def run(self, *, root: Path | None = None) -> AuditRunResult:
        return AuditRunResult(
            name=self.name,
            success=True,
            message=f"wrote {self.output_file}",
            output_path=None,
        )


def _write_sample_workspace(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "workspace"\n', encoding="utf-8"
    )
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
        env_prefix="LEX_APP__",
        env_nested_delimiter="__",
    )
    debug: bool = Field(default=False, description="Enable debug mode.")
    nested: NestedConfig = NestedConfig()
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_cli_lists_generators(capsys) -> None:
    exit_code = main(["audit", "list"])
    output_lines = capsys.readouterr().out.strip().splitlines()

    assert exit_code == 0
    assert output_lines[0] == "name\tdescription"
    assert [line.split("\t", 1)[0] for line in output_lines[1:]] == list(
        build_audit_registry().names()
    )


def test_cli_runs_single_generator_successfully(tmp_path: Path, capsys) -> None:
    _write_sample_workspace(tmp_path)

    exit_code = main(["audit", "run", "env_vars", "--root", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "env_vars: wrote" in output
    assert (tmp_path / "docs/audit" / "AUDIT_ENV_VARS.md").exists()


def test_cli_validates_registered_generators(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    registry = GeneratorRegistry[_FakeAuditGenerator]()
    for generator in (
        _FakeAuditGenerator("quality", "Quality audit", "AUDIT_QUALITY.md"),
        _FakeAuditGenerator("rules", "Rules audit", "AUDIT_RULES.md"),
        _FakeAuditGenerator("tests", "Tests audit", "AUDIT_TESTS.md"),
    ):
        registry.register(generator.name, generator)

    (tmp_path / "AUDIT_QUALITY.md").write_text(
        """
# AUDIT_QUALITY.md

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **PASS** | 0 | 10 ms | `uv run ruff check .` |
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
| critical | 0 |
| important | 0 |
| minor | 0 |

## Package Coverage

- Discovered packages: 1
- Covered packages: 1
- Missing packages: 0
- Coverage status: **PASS**
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
| Scripts audit smoke | `tests/dev` | `uv run pytest tests/dev -q --no-cov` | 0 | 11 ms | `2 passed in 0.11s` | none |
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("dev.cli._get_registry", lambda: registry)

    exit_code = main(["audit", "validate", "--root", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "validated 3 audit generator(s)" in output


def test_cli_validate_fails_when_required_reports_or_evidence_are_missing(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    registry = GeneratorRegistry[_FakeAuditGenerator]()
    for generator in (
        _FakeAuditGenerator("quality", "Quality audit", "AUDIT_QUALITY.md"),
        _FakeAuditGenerator("rules", "Rules audit", "AUDIT_RULES.md"),
        _FakeAuditGenerator("tests", "Tests audit", "AUDIT_TESTS.md"),
    ):
        registry.register(generator.name, generator)

    (tmp_path / "AUDIT_QUALITY.md").write_text("# AUDIT_QUALITY.md\n\nmissing evidence\n", encoding="utf-8")
    (tmp_path / "AUDIT_RULES.md").write_text(
        """
# AUDIT_RULES.md

## Severity Summary

| Severity | Count |
|----------|-------|
| critical | 1 |
| important | 2 |
| minor | 0 |

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

    monkeypatch.setattr("dev.cli._get_registry", lambda: registry)

    exit_code = main(["audit", "validate", "--root", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "missing required report: AUDIT_TESTS.md" in captured.err
    assert "quality: missing required evidence" in captured.err
    assert "rules: package coverage gaps detected" in captured.err
    assert "rules: critical violations exceed threshold" in captured.err


def test_cli_validate_passes_with_required_reports_and_evidence(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    registry = GeneratorRegistry[_FakeAuditGenerator]()
    for generator in (
        _FakeAuditGenerator("quality", "Quality audit", "AUDIT_QUALITY.md"),
        _FakeAuditGenerator("rules", "Rules audit", "AUDIT_RULES.md"),
        _FakeAuditGenerator("tests", "Tests audit", "AUDIT_TESTS.md"),
    ):
        registry.register(generator.name, generator)

    (tmp_path / "AUDIT_QUALITY.md").write_text(
        """
# AUDIT_QUALITY.md

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **PASS** | 0 | 10 ms | `uv run ruff check .` |
| `Mypy` | **PASS** | 0 | 20 ms | `uv run mypy lexigram/src/` |
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
| critical | 0 |
| important | 2 |
| minor | 1 |

## Package Coverage

- Discovered packages: 3
- Covered packages: 3
- Missing packages: 0
- Coverage status: **PASS**
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
| Scripts audit smoke | `tests/dev` | `uv run pytest tests/dev -q --no-cov` | 0 | 11 ms | `2 passed in 0.11s` | none |
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("dev.cli._get_registry", lambda: registry)

    exit_code = main(["audit", "validate", "--root", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "validated 3 audit generator(s)" in output
