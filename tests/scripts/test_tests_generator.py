from __future__ import annotations

from pathlib import Path

from scripts.audit.generators import tests as tests_generator_module
from scripts.audit.generators.tests import TestsAuditGenerator
from scripts.core.evidence import CommandEvidence

SCRIPTS_COMMAND = ("uv", "run", "pytest", "tests/scripts", "-q", "-m", "not integration", "--cov=scripts")
FRAMEWORK_COMMAND = ("uv", "run", "pytest", "lexigram/tests", "-q", "-m", "not integration", "--cov=lexigram")
CONTRACTS_PACKAGE_COMMAND = ("uv", "run", "pytest", "lexigram-contracts/tests", "-q", "-m", "not integration", "--cov=lexigram.contracts")
AUTH_PACKAGE_COMMAND = ("uv", "run", "pytest", "lexigram-auth/tests", "-q", "-m", "not integration", "--cov=lexigram.auth")


def _write_sample_workspace(root: Path) -> None:
    (root / "pyproject.toml").write_text('[project]\nname = "workspace"\n', encoding="utf-8")
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
    contracts_package_root = root / "lexigram-contracts"
    contracts_package_root.mkdir()
    (contracts_package_root / "pyproject.toml").write_text(
        '[project]\nname = "lexigram-contracts"\n',
        encoding="utf-8",
    )
    contracts_source_dir = contracts_package_root / "src" / "lexigram" / "contracts"
    contracts_source_dir.mkdir(parents=True)
    (contracts_source_dir / "__init__.py").write_text("", encoding="utf-8")
    contracts_tests_dir = contracts_package_root / "tests"
    contracts_tests_dir.mkdir()
    (contracts_tests_dir / "test_contracts.py").write_text(
        "from __future__ import annotations\n\n\ndef test_contracts() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    auth_package_root = root / "lexigram-auth"
    auth_package_root.mkdir()
    (auth_package_root / "pyproject.toml").write_text(
        '[project]\nname = "lexigram-auth"\n',
        encoding="utf-8",
    )
    auth_source_dir = auth_package_root / "src" / "lexigram" / "auth"
    auth_source_dir.mkdir(parents=True)
    (auth_source_dir / "__init__.py").write_text("", encoding="utf-8")
    auth_tests_dir = auth_package_root / "tests"
    auth_tests_dir.mkdir()
    (auth_tests_dir / "test_auth_sample.py").write_text(
        "from __future__ import annotations\n\n\ndef test_auth_sample() -> None:\n    assert True\n",
        encoding="utf-8",
    )



def test_tests_generator_includes_labeled_execution_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_sample_workspace(tmp_path)
    observed_commands: list[tuple[tuple[str, ...], Path | None, float | None]] = []

    def fake_run_command(command: tuple[str, ...], *, cwd: Path | None = None, timeout=None):
        observed_commands.append((command, cwd, timeout))
        if command == SCRIPTS_COMMAND:
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout="..\n2 passed in 0.12s\n",
                stderr="",
                duration_ms=123,
            )
        if command == FRAMEWORK_COMMAND:
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout="....\n4 passed, 1 skipped, 1 warning in 0.08s\n",
                stderr="",
                duration_ms=98,
            )
        if command == CONTRACTS_PACKAGE_COMMAND:
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout="..\n2 passed in 0.05s\nTOTAL 2 0 100%\n",
                stderr="",
                duration_ms=50,
            )
        if command == AUTH_PACKAGE_COMMAND:
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout=".\n1 passed in 0.03s\nTOTAL 1 0 100%\n",
                stderr="",
                duration_ms=35,
            )
        raise AssertionError(f"Unexpected command: {command!r}")

    monkeypatch.setattr(tests_generator_module, "run_command", fake_run_command)
    generator = TestsAuditGenerator()

    result = generator.run(root=tmp_path, all_mode=True)
    markdown = (tmp_path / "AUDIT_TESTS.md").read_text(encoding="utf-8")

    assert result.success is True
    assert "# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit" in markdown
    assert "## Summary" in markdown
    assert "- Total passed tests: 9" in markdown
    assert "- Total failed tests: 0" in markdown
    assert "- Total skipped tests: 1" in markdown
    assert "- Total warnings: 1" in markdown
    assert "- Aggregate code coverage: 100.00%" in markdown
    assert "## Execution Evidence" in markdown
    assert "| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |" in markdown
    assert "Scripts audit smoke" in markdown
    assert "Lexigram framework core tests" in markdown
    assert "Package tests: lexigram-contracts" in markdown
    assert "`tests/scripts`" in markdown
    assert "`lexigram/tests`" in markdown
    assert "`lexigram-contracts/tests`" in markdown
    assert "`lexigram-auth/tests`" in markdown
    assert "- Parsed summary: `2 passed in 0.12s`" in markdown
    assert "- Parsed summary: `4 passed, 1 skipped, 1 warning in 0.08s`" in markdown
    assert "passed=4, total=5, failed=0, skipped=1, warnings=1, coverage=0.0%" in markdown
    assert "passed=1, total=1, failed=0, skipped=0, warnings=0, coverage=100.0%" in markdown
    assert observed_commands == [
        (FRAMEWORK_COMMAND, tmp_path, 120.0),
        (CONTRACTS_PACKAGE_COMMAND, tmp_path, 120.0),
        (AUTH_PACKAGE_COMMAND, tmp_path, 120.0),
        (SCRIPTS_COMMAND, tmp_path, 120.0),
    ]



def test_tests_generator_renders_failed_command_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_sample_workspace(tmp_path)

    def fake_run_command(command: tuple[str, ...], *, cwd: Path | None = None, timeout=None):
        if command == SCRIPTS_COMMAND:
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout="..\n2 passed in 0.12s\n",
                stderr="",
                duration_ms=123,
            )
        if command == FRAMEWORK_COMMAND:
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=1,
                stdout=(
                    ".F\n"
                    "FAILED lexigram/tests/test_sample.py::test_sample - AssertionError: boom\n"
                    "1 failed, 1 passed in 0.34s\n"
                ),
                stderr="",
                duration_ms=456,
            )
        if command == CONTRACTS_PACKAGE_COMMAND:
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout=".\n1 passed in 0.05s\n",
                stderr="",
                duration_ms=50,
            )
        if command == AUTH_PACKAGE_COMMAND:
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout=".\n1 passed in 0.03s\n",
                stderr="",
                duration_ms=35,
            )
        raise AssertionError(f"Unexpected command: {command!r}")

    monkeypatch.setattr(tests_generator_module, "run_command", fake_run_command)
    generator = TestsAuditGenerator()

    result = generator.run(root=tmp_path, all_mode=True)
    markdown = (tmp_path / "AUDIT_TESTS.md").read_text(encoding="utf-8")

    assert result.success is True
    assert "## Execution Evidence" in markdown
    assert "- Exit code: `1`" in markdown
    assert "- Duration: `456 ms`" in markdown
    assert "- Parsed summary: `1 failed, 1 passed in 0.34s`" in markdown
    assert "lexigram/tests/test_sample.py::test_sample" in markdown



def test_tests_generator_renders_timeout_evidence_with_scope_label(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_sample_workspace(tmp_path)

    def fake_run_command(command: tuple[str, ...], *, cwd: Path | None = None, timeout=None):
        if command == SCRIPTS_COMMAND:
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
        if command == FRAMEWORK_COMMAND:
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout=".\n1 passed in 0.08s\n",
                stderr="",
                duration_ms=98,
            )
        if command == CONTRACTS_PACKAGE_COMMAND:
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout=".\n1 passed in 0.05s\n",
                stderr="",
                duration_ms=50,
            )
        if command == AUTH_PACKAGE_COMMAND:
            return CommandEvidence(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout,
                exit_code=0,
                stdout=".\n1 passed in 0.03s\n",
                stderr="",
                duration_ms=35,
            )
        raise AssertionError(f"Unexpected command: {command!r}")

    monkeypatch.setattr(tests_generator_module, "run_command", fake_run_command)
    generator = TestsAuditGenerator()

    result = generator.run(root=tmp_path, all_mode=True)
    markdown = (tmp_path / "AUDIT_TESTS.md").read_text(encoding="utf-8")

    assert result.success is True
    assert "Scripts audit smoke" in markdown
    assert "`tests/scripts`" in markdown
    assert "- Exit code: `timeout`" in markdown
    assert "- Parsed summary: `timed out after 120.0 seconds`" in markdown
    assert "(no output)" in markdown
