from __future__ import annotations

from pathlib import Path

from dev.audit.generators import quality
from dev.audit.generators.quality import QualityAuditGenerator
from dev.core.evidence import CommandEvidence


def _write_sample_workspace(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "workspace"\n\n[tool.uv.workspace]\n'
        'members = ["lexigram", "lexigram-ai-demo"]\n',
        encoding="utf-8",
    )
    package_root = root / "lexigram"
    package_root.mkdir()
    (package_root / "pyproject.toml").write_text(
        '[project]\nname = "lexigram"\n',
        encoding="utf-8",
    )
    source_dir = package_root / "src" / "lexigram"
    source_dir.mkdir(parents=True)
    (source_dir / "__init__.py").write_text("", encoding="utf-8")
    tests_dir = package_root / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_sample.py").write_text(
        "from __future__ import annotations\n\n\ndef test_sample() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    extension_root = root / "lexigram-ai-demo"
    extension_root.mkdir()
    (extension_root / "pyproject.toml").write_text(
        '[project]\nname = "lexigram-ai-demo"\n',
        encoding="utf-8",
    )
    extension_source_dir = extension_root / "src" / "lexigram_ai_demo"
    extension_source_dir.mkdir(parents=True)
    (extension_source_dir / "__init__.py").write_text("", encoding="utf-8")


def test_quality_generator_includes_ruff_and_mypy_tool_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_sample_workspace(tmp_path)
    observed_commands: list[tuple[tuple[str, ...], Path | None, float | None]] = []

    def fake_run_command(command: tuple[str, ...], *, cwd: Path | None = None, timeout=None):
        observed_commands.append((command, cwd, timeout))
        if command == ("uv", "run", "ruff", "check", "."):
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout="All checks passed!\n",
                stderr="",
                duration_ms=145,
            )
        if command == ("uv", "run", "mypy", "src") and cwd is not None and cwd.name == "lexigram":
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=1,
                stdout="",
                stderr="src/lexigram/demo.py:10: error: Example failure [attr-defined]\n",
                duration_ms=200,
            )
        if command == ("uv", "run", "mypy", "src") and cwd is not None and cwd.name == "lexigram-ai-demo":
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout="Success: no issues found\n",
                stderr="",
                duration_ms=122,
            )
        if command == ("uv", "run", "mypy", "src/"):
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout="Success: no issues found\n",
                stderr="",
                duration_ms=122,
            )
        raise AssertionError(f"Unexpected command: {command!r}")

    monkeypatch.setattr(quality, "run_command", fake_run_command)
    generator = QualityAuditGenerator()

    result = generator.run(root=tmp_path)
    markdown = (tmp_path / "docs/audit" / "AUDIT_QUALITY.md").read_text(encoding="utf-8")

    assert result.success is True
    assert "## Tool Results" in markdown
    assert "| `Ruff` | **PASS** | 0 | 145 ms | `uv run ruff check .` |" in markdown
    assert (
        "| `Mypy` | **FAIL** | 1 | 322 ms | "
        "`uv run mypy src/ (per-package across 2 packages)` |"
    ) in markdown
    assert "- Status: **PASS**" in markdown
    assert "- Exit code: `0`" in markdown
    assert "- Duration: `145 ms`" in markdown
    assert "All checks passed!" in markdown
    assert "- Status: **FAIL**" in markdown
    assert "- Exit code: `1`" in markdown
    assert "- Duration: `322 ms`" in markdown
    assert "[lexigram] 1 errors" in markdown
    assert observed_commands == [
        (("uv", "run", "ruff", "check", "."), tmp_path, 120.0),
        (("uv", "run", "mypy", "src"), tmp_path / "lexigram", 60.0),
        (
            ("uv", "run", "mypy", "src"),
            tmp_path / "lexigram-ai-demo",
            60.0,
        ),
    ]


def test_quality_generator_writes_report_for_timeout_and_command_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_sample_workspace(tmp_path)

    def fake_run_command(command: tuple[str, ...], *, cwd: Path | None = None, timeout=None):
        if command == ("uv", "run", "ruff", "check", "."):
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=None,
                stdout="",
                stderr="",
                duration_ms=120000,
                timed_out=True,
            )
        if command[:3] == ("uv", "run", "mypy"):
            raise OSError("mypy executable missing")
        raise AssertionError(f"Unexpected command: {command!r}")

    monkeypatch.setattr(quality, "run_command", fake_run_command)
    generator = QualityAuditGenerator()

    result = generator.run(root=tmp_path)
    markdown = (tmp_path / "docs/audit" / "AUDIT_QUALITY.md").read_text(encoding="utf-8")

    assert result.success is True
    assert "## Tool Results" in markdown
    assert "| `Ruff` | **FAIL** | timeout | 120000 ms | `uv run ruff check .` |" in markdown
    assert "(no output)" in markdown
    assert "mypy executable missing" in markdown
    assert "| `Mypy` | **FAIL** | error | 0 ms | `uv run mypy" in markdown


def test_quality_generator_surfaces_mypy_crash_without_parseable_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A non-zero mypy exit with no ``error:`` lines reports a crash, not 0 errors."""
    _write_sample_workspace(tmp_path)

    def fake_run_command(command: tuple[str, ...], *, cwd: Path | None = None, timeout=None):
        if command == ("uv", "run", "ruff", "check", "."):
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout="All checks passed!\n",
                stderr="",
                duration_ms=100,
            )
        if command[:3] == ("uv", "run", "mypy"):
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=2,
                stdout="",
                stderr=(
                    "mypy: warning: missing library stubs\n"
                    "{{ package_name }} contains __init__.py but is not a valid "
                    "Python package name\n"
                ),
                duration_ms=150,
            )
        raise AssertionError(f"Unexpected command: {command!r}")

    monkeypatch.setattr(quality, "run_command", fake_run_command)
    generator = QualityAuditGenerator()

    generator.run(root=tmp_path)
    markdown = (tmp_path / "docs/audit" / "AUDIT_QUALITY.md").read_text(encoding="utf-8")

    # The misleading "[pkg] 0 errors" line must not appear...
    assert "0 errors" not in markdown
    # ...replaced by an explicit crash report carrying the real stderr tail.
    assert "crashed (exit 2, 0 parseable errors)" in markdown
    assert "not a valid Python package name" in markdown
