from __future__ import annotations

from datetime import date
from pathlib import Path

from dev.audit.generators import security
from dev.audit.generators.security import SecurityAuditGenerator
from dev.core.evidence import CommandEvidence
from dev.core.rule_engine import RuleSeverity
from dev.core.rules_catalog import make_rule_finding

TRACKER_FIXTURE = """\
| # | Area | Severity mix | Spec | Plan |
|---|------|--------------|------|------|
| 1 | **P0 session-secret** | Critical \u00d73 | `specs/x.md` | `plans/x.md` — **EXECUTED 2026-08-16** |
| 50 | **Redis persistence fails open** | Critical \u00d71 | `specs/y.md` | Not yet written |
"""

RUFF_CLEAN = "All checks passed!\n"
RUFF_DIRTY = (
    "lexigram-web/src/lexigram/web/app.py:40:9: S608 Possible SQL injection vector through string-based query construction\n"
    "lexigram/src/lexigram/dispatcher.py:12:5: S101 Use of `assert` detected\n"
    "Found 2 errors.\n"
)
PIP_CLEAN = "No known vulnerabilities found\n"
PIP_DIRTY = "Found 3 known vulnerabilities in 2 packages\n"


def _write_workspace(tmp_path: Path, *, tracker: bool = True) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "workspace"\n', encoding="utf-8"
    )
    (tmp_path / "lexigram").mkdir()
    (tmp_path / "lexigram" / "pyproject.toml").write_text(
        '[project]\nname = "lexigram"\n', encoding="utf-8"
    )
    if tracker:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "AUDIT_TRACKER.md").write_text(TRACKER_FIXTURE, encoding="utf-8")


def _evidence(
    command: tuple[str, ...], stdout: str, exit_code: int = 0
) -> CommandEvidence:
    return CommandEvidence(
        command=command,
        cwd=None,
        timeout_seconds=None,
        exit_code=exit_code,
        stdout=stdout,
        stderr="",
        duration_ms=100,
    )


def _fake_run_rules(*_args: object, **_kwargs: object) -> object:
    result = object.__new__(type("FakeResult", (), {}))
    result.findings = ()
    return result


def test_security_generator_verdict_critical_with_open_critical_row(
    tmp_path: Path, monkeypatch
) -> None:
    _write_workspace(tmp_path)

    def fake_run_command(command: tuple[str, ...], *, cwd=None, timeout=None):
        if command == ("uv", "run", "pip-audit", "--timeout", "60"):
            return _evidence(command, PIP_CLEAN)
        if command == (
            "uv",
            "run",
            "ruff",
            "check",
            ".",
            "--select",
            "S",
            "--output-format",
            "concise",
        ):
            return _evidence(command, RUFF_CLEAN)
        raise AssertionError(f"unexpected command {command!r}")

    monkeypatch.setattr(security, "run_command", fake_run_command)
    monkeypatch.setattr(security, "run_rules", _fake_run_rules)
    generator = SecurityAuditGenerator()
    result = generator.run(root=tmp_path)
    markdown = (tmp_path / "docs/lexigram-docs/audit" / "AUDIT_SECURITY.md").read_text(
        encoding="utf-8"
    )
    assert result.success is True
    assert "**CRITICAL**" in markdown
    assert "## Dependency Scan" in markdown
    assert "## Static Analysis (ruff bandit rules)" in markdown
    assert "## Audit Tracker Status" in markdown
    assert "| 50 |" in markdown
    assert f"(reviewed {date.today().isoformat()}; all closed — see notes below)" in markdown


def test_security_generator_parses_ruff_and_pip_evidence(
    tmp_path: Path, monkeypatch
) -> None:
    _write_workspace(tmp_path)

    def fake_run_command(command: tuple[str, ...], *, cwd=None, timeout=None):
        if command == ("uv", "run", "pip-audit", "--timeout", "60"):
            return _evidence(command, PIP_DIRTY)
        if command == (
            "uv",
            "run",
            "ruff",
            "check",
            ".",
            "--select",
            "S",
            "--output-format",
            "concise",
        ):
            return _evidence(command, RUFF_DIRTY, exit_code=1)
        raise AssertionError(f"unexpected command {command!r}")

    def fake_run_rules(*_args: object, **_kwargs: object) -> object:
        finding = make_rule_finding(
            rule_id="sec-jwt-verification-disabled",
            severity=RuleSeverity.CRITICAL,
            owner="security",
            rationale="verification must stay on",
            package_name="lexigram",
            path=Path("lexigram/src/lexigram/jwt.py"),
            line=7,
            message="accepts the unsigned 'none' JWT algorithm.",
        )
        result = object.__new__(type("FakeResult", (), {}))
        result.findings = (finding,)
        return result

    monkeypatch.setattr(security, "run_command", fake_run_command)
    monkeypatch.setattr(security, "run_rules", fake_run_rules)
    markdown = tmp_path / "docs/lexigram-docs/audit" / "AUDIT_SECURITY.md"
    generator = SecurityAuditGenerator()
    result = generator.run(root=tmp_path)
    assert result.success is True
    text = markdown.read_text(encoding="utf-8")
    assert "Found 3 known vulnerabilities in 2 packages" in text
    assert "S608" in text
    assert "S101" in text
    assert "sec-jwt-verification-disabled" in text
    assert "## Framework Security Rules" in text
    assert "## Open Risk Table" in text


def test_security_generator_pip_audit_fallback(tmp_path: Path, monkeypatch) -> None:
    _write_workspace(tmp_path)
    commands: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...], *, cwd=None, timeout=None):
        commands.append(command)
        if command == ("uv", "run", "pip-audit", "--timeout", "60"):
            return _evidence(command, "No module named pip_audit", exit_code=2)
        if command == ("uvx", "pip-audit"):
            return _evidence(command, PIP_CLEAN)
        if command == (
            "uv",
            "run",
            "ruff",
            "check",
            ".",
            "--select",
            "S",
            "--output-format",
            "concise",
        ):
            return _evidence(command, RUFF_CLEAN)
        raise AssertionError(f"unexpected command {command!r}")

    monkeypatch.setattr(security, "run_command", fake_run_command)
    monkeypatch.setattr(security, "run_rules", _fake_run_rules)
    generator = SecurityAuditGenerator()
    result = generator.run(root=tmp_path)
    assert result.success is True
    assert ("uvx", "pip-audit") in commands


def test_security_generator_handles_missing_tracker(
    tmp_path: Path, monkeypatch
) -> None:
    _write_workspace(tmp_path, tracker=False)

    def fake_run_command(command: tuple[str, ...], *, cwd=None, timeout=None):
        if command == ("uv", "run", "pip-audit", "--timeout", "60"):
            return _evidence(command, PIP_CLEAN)
        if command == (
            "uv",
            "run",
            "ruff",
            "check",
            ".",
            "--select",
            "S",
            "--output-format",
            "concise",
        ):
            return _evidence(command, RUFF_CLEAN)
        raise AssertionError(f"unexpected command {command!r}")

    monkeypatch.setattr(security, "run_command", fake_run_command)
    monkeypatch.setattr(security, "run_rules", _fake_run_rules)
    markdown = tmp_path / "docs/lexigram-docs/audit" / "AUDIT_SECURITY.md"
    generator = SecurityAuditGenerator()
    result = generator.run(root=tmp_path)
    assert result.success is True
    assert "not found" in markdown.read_text(encoding="utf-8").lower()
