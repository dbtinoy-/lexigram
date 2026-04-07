from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from time import perf_counter

from scripts.audit.generators.base import MarkdownAuditGenerator
from scripts.core.command_runner import run_command
from scripts.core.evidence import CommandEvidence

TEST_COMMAND_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True, slots=True)
class TestCommandSpec:
    """A labeled pytest command rendered in the execution-evidence report."""

    label: str
    scope: str
    kind: str
    command: tuple[str, ...]


class TestsAuditGenerator(MarkdownAuditGenerator):
    """Generate a test audit with live pytest execution evidence."""

    name = "tests"
    description = "Generate AUDIT_TESTS.md from pytest execution evidence and test discovery."
    output_file = "AUDIT_TESTS.md"

    def render_markdown(self, *, root: Path) -> str:
        """Render markdown with execution evidence and supporting inventory."""

        package_rows = [_tests_row(path, root) for path in self.iter_package_roots(root=root)]
        package_rows = [row for row in package_rows if row["test_files"]]
        all_mode = getattr(self, "_all_mode", False)
        command_specs = _build_test_command_specs(root=root, package_rows=package_rows, all_mode=all_mode)
        execution_results = tuple(
            _run_test_command(spec=spec, root=root)
            for spec in command_specs
        )
        
        # Calculate aggregate coverage
        results_with_cov = [r for r in execution_results if r["coverage"] > 0]
        avg_coverage = sum(r["coverage"] for r in results_with_cov) / len(results_with_cov) if results_with_cov else 0
        
        markdown = """# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

"""
        markdown += f"- Total passed tests: {sum(result['passed'] for result in execution_results)}\n"
        markdown += f"- Total failed tests: {sum(result['failed'] for result in execution_results)}\n"
        markdown += f"- Total skipped tests: {sum(result['skipped'] for result in execution_results)}\n"
        markdown += f"- Total warnings: {sum(result['warnings'] for result in execution_results)}\n"
        markdown += f"- Aggregate code coverage: {avg_coverage:.2f}%\n"
        markdown += "\n"
        markdown += f"- Representative commands run: {len(execution_results)}\n"
        markdown += (
            f"- Commands passing: {sum(1 for result in execution_results if result['status'] == 'PASS')}\n"
        )
        markdown += (
            f"- Commands failing: {sum(1 for result in execution_results if result['status'] == 'FAIL')}\n"
        )
        markdown += f"- Packages with tests: {len(package_rows)}\n"
        markdown += f"- Test files: {sum(row['test_files'] for row in package_rows)}\n"
        markdown += f"- Test functions: {sum(row['test_functions'] for row in package_rows)}\n\n"
        
        markdown += "### Exit Codes Reference\n\n"
        markdown += "- **`0`**: Success — All tests passed and code coverage met the configured threshold.\n"
        markdown += "- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.\n"
        markdown += "- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.\n\n"
        
        markdown += "## Execution Evidence\n\n"
        markdown += (
            "| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |\n"
        )
        markdown += (
            "|-------|---------------|------------|---------|----------|------|-----------|----------|\n"
        )
        for result in execution_results:
            markdown += (
                f"| {result['label']} | {result['coverage']}% | "
                f"{result['passed']}/{result['total']} | "
                f"{result['failed']} | {result['skipped']} | {result['warnings']} | "
                f"{result['exit_code']} | "
                f"{result['duration_ms']} ms |\n"
            )
        markdown += "\n"
        markdown += "### Execution Scope Notes\n\n"
        markdown += "- `framework-core`: real test execution for `lexigram/tests`.\n"
        markdown += "- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.\n"
        if all_mode:
            markdown += "- `scripts-audit`: real test execution for `tests/scripts`.\n\n"
        for result in execution_results:
            markdown += f"### {result['label']}\n\n"
            markdown += f"- Scope: `{result['scope']}`\n"
            markdown += f"- Command: `{result['command_text']}`\n"
            markdown += f"- Status: **{result['status']}**\n"
            markdown += f"- Exit code: `{result['exit_code']}`\n"
            markdown += f"- Duration: `{result['duration_ms']} ms`\n"
            markdown += f"- Parsed summary: `{result['parsed_summary']}`\n"
            markdown += (
                f"- Counters: passed={result['passed']}, total={result['total']}, "
                f"failed={result['failed']}, skipped={result['skipped']}, "
                f"warnings={result['warnings']}, coverage={result['coverage']}%\n"
            )
            markdown += f"- Example failures: {result['example_failures_text']}\n"
            markdown += "- Output snippet:\n\n"
            markdown += "```text\n"
            markdown += f"{result['snippet']}\n"
            markdown += "```\n\n"
        return markdown


def _tests_row(package_path: Path, root: Path) -> dict[str, int | str]:
    """Count test files and functions for a package."""

    test_files = sorted(package_path.glob("tests/**/*.py"))
    test_functions = 0
    pattern = re.compile(r"^\s*(?:async\s+def|def)\s+test_", flags=re.MULTILINE)
    for file_path in test_files:
        test_functions += len(pattern.findall(file_path.read_text(encoding="utf-8")))
    return {
        "name": str(package_path.relative_to(root)),
        "test_files": len(test_files),
        "test_functions": test_functions,
    }


def _build_test_command_specs(
    *,
    root: Path,
    package_rows: list[dict[str, int | str]],
    all_mode: bool = False,
) -> tuple[TestCommandSpec, ...]:
    """Build the targeted pytest commands shown in the report."""

    specs: list[TestCommandSpec] = []
    
    # Extract the core lexigram package if present and build its scope separately
    core_package = next((row for row in package_rows if str(row["name"]) == "lexigram"), None)
    if core_package:
        specs.append(
            TestCommandSpec(
                label="Lexigram framework core tests",
                scope="lexigram/tests",
                kind="framework-core",
                command=("uv", "run", "pytest", "lexigram/tests", "-q", "--cov=lexigram"),
            )
        )
        
    contracts_package = next((row for row in package_rows if str(row["name"]) == "lexigram-contracts"), None)
    if contracts_package:
        specs.append(
            TestCommandSpec(
                label="Package tests: lexigram-contracts",
                scope="lexigram-contracts/tests",
                kind="package",
                command=("uv", "run", "pytest", "lexigram-contracts/tests", "-q", "--cov=lexigram.contracts"),
            )
        )
    
    package_scopes = sorted(
        (
            f"{row['name']}/tests",
            str(row["name"]),
        )
        for row in package_rows
        if str(row["name"]) not in {"lexigram", "lexigram-contracts"}
    )
    for scope, package_name in package_scopes:
        kind = "package"
        label = f"Package tests: {package_name}"
        
        cov_module = package_name.replace("-", ".")
        if package_name == "lexigram-sql":
            label = f"Package tests: {package_name} (unit only, no external DB)"
            command = ("uv", "run", "pytest", f"{scope}/unit", "-q", f"--cov={cov_module}")
        else:
            command = ("uv", "run", "pytest", scope, "-q", f"--cov={cov_module}")
            
        specs.append(
            TestCommandSpec(
                label=label,
                scope=scope,
                kind=kind,
                command=command,
            )
        )
    
    if all_mode:
        specs.append(
            TestCommandSpec(
                label="Scripts audit smoke",
                scope="tests/scripts",
                kind="scripts-audit",
                command=("uv", "run", "pytest", "tests/scripts", "-q", "--cov=scripts"),
            )
        )
    return tuple(specs)


def _run_test_command(
    *,
    spec: TestCommandSpec,
    root: Path,
) -> dict[str, str | int]:
    """Run a representative pytest command and normalize its evidence."""

    started_at = perf_counter()
    try:
        evidence = run_command(
            spec.command,
            cwd=root,
            timeout=TEST_COMMAND_TIMEOUT_SECONDS,
        )
    except OSError as exc:
        return _test_result(
            spec=spec,
            exit_code="error",
            duration_ms=int((perf_counter() - started_at) * 1000),
            parsed_summary=f"command execution failed: {exc}",
            example_failures=(),
            snippet=f"Command execution failed: {exc}",
            status="FAIL",
        )

    return _test_result(
        spec=spec,
        exit_code=_format_exit_code(evidence),
        duration_ms=evidence.duration_ms,
        parsed_summary=_parse_pytest_summary(evidence),
        example_failures=_parse_failed_examples(evidence),
        counts=_extract_counts(evidence),
        snippet=_output_snippet(evidence),
        status=_command_status(evidence),
    )


def _test_result(
    *,
    spec: TestCommandSpec,
    exit_code: str,
    duration_ms: int,
    parsed_summary: str,
    example_failures: tuple[str, ...],
    counts: dict[str, int | float],
    snippet: str,
    status: str,
) -> dict[str, str | int | float]:
    """Build a markdown-friendly result row for one test command."""

    counters = counts or {
        "failed": 0,
        "skipped": 0,
        "warnings": 0,
        "passed": 0,
        "total": 0,
        "coverage": 0.0,
    }

    return {
        "label": spec.label,
        "scope": spec.scope,
        "kind": spec.kind,
        "command_text": " ".join(spec.command),
        "status": status,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "parsed_summary": parsed_summary,
        "failed": counters["failed"],
        "skipped": counters["skipped"],
        "warnings": counters["warnings"],
        "passed": counters["passed"],
        "total": counters["total"],
        "coverage": counters["coverage"],
        "example_failures_inline": (
            ", ".join(f"`{test_id}`" for test_id in example_failures) if example_failures else "none"
        ),
        "example_failures_text": (
            ", ".join(f"`{test_id}`" for test_id in example_failures) if example_failures else "none"
        ),
        "snippet": snippet,
    }


def _command_status(evidence: CommandEvidence) -> str:
    """Return PASS or FAIL for a pytest command invocation."""

    if evidence.timed_out:
        return "FAIL"
    if evidence.exit_code == 0:
        return "PASS"
    return "FAIL"


def _format_exit_code(evidence: CommandEvidence) -> str:
    """Format exit-code values for markdown output."""

    if evidence.exit_code is None:
        return "timeout"
    return str(evidence.exit_code)


def _parse_pytest_summary(evidence: CommandEvidence) -> str:
    """Extract a compact pytest summary line from command output."""

    combined_output = _combined_output(evidence)
    for line in reversed(combined_output.splitlines()):
        candidate = line.strip().strip("=")
        if not candidate:
            continue
        if not re.search(
            r"\d+\s+(?:passed|failed|error|errors|skipped|xfailed|xpassed|rerun|reruns)",
            candidate,
        ):
            continue
        if " in " in candidate:
            return candidate
        return candidate
    if evidence.timed_out:
        return f"timed out after {TEST_COMMAND_TIMEOUT_SECONDS} seconds"
    if evidence.exit_code is None:
        return "no exit code captured"
    return "summary unavailable"


def _parse_failed_examples(evidence: CommandEvidence) -> tuple[str, ...]:
    """Extract a few failed test identifiers from pytest output."""

    failures: list[str] = []
    seen: set[str] = set()
    for line in _combined_output(evidence).splitlines():
        match = re.match(r"^FAILED\s+([^\s]+)", line.strip())
        if match is None:
            continue
        test_id = match.group(1)
        if test_id in seen:
            continue
        failures.append(test_id)
        seen.add(test_id)
        if len(failures) == 5:
            break
    return tuple(failures)


def _output_snippet(evidence: CommandEvidence) -> str:
    """Return a short snippet from pytest output."""

    output = _combined_output(evidence).strip()
    if not output:
        return "(no output)"
    lines = output.splitlines()
    snippet = "\n".join(lines[:12])
    if len(lines) > 12:
        snippet += "\n..."
    return snippet[:800]


def _combined_output(evidence: CommandEvidence) -> str:
    """Join stdout and stderr for parsing and display."""

    parts = [part.strip() for part in (evidence.stdout, evidence.stderr) if part.strip()]
    return "\n".join(parts)


def _extract_counts(evidence: CommandEvidence) -> dict[str, int | float]:
    """Extract key pytest counters and coverage from command output."""

    counts = {"failed": 0, "skipped": 0, "warnings": 0, "passed": 0, "total": 0, "coverage": 0.0}
    combined = _combined_output(evidence)
    
    # Parse pytest results from summary line
    # Match something like "2 failed, 216 passed, 4 warnings in 1.21s"
    # Pytest output usually ends with "== 1 failed, 215 passed, 4 warnings in 1.21s =="
    summary_pattern = r"(\d+)\s+(passed|failed|skipped|warning|warnings|error|errors|xfailed|xpassed)"
    for value, label in re.findall(summary_pattern, combined, flags=re.IGNORECASE):
        n = int(value)
        normalized = label.lower()
        if normalized == "passed":
            counts["passed"] = n
        elif normalized in {"failed", "error", "errors"}:
            counts["failed"] += n
        elif normalized == "skipped":
            counts["skipped"] = n
        elif normalized in {"warning", "warnings"}:
            counts["warnings"] = n
        elif normalized == "xfailed":
            # xfailed are expected failures, we'll treat them as skipped for total count purposes or just ignore?
            # Usually they don't cause exit code 1.
            pass
            
    counts["total"] = counts["passed"] + counts["failed"] + counts["skipped"]

    # Parse coverage TOTAL line
    # Example: "TOTAL                                                                    1408    989    30%"
    cov_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", combined)
    if cov_match:
        counts["coverage"] = float(cov_match.group(1))
        
    return counts
