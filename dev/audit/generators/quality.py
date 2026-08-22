from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from time import perf_counter

from dev.audit.generators.base import MarkdownAuditGenerator
from dev.core.command_runner import run_command
from dev.core.evidence import CommandEvidence

QUALITY_TOOL_TIMEOUT_SECONDS = 120.0
MYPY_TIMEOUT_PER_PACKAGE = 60.0


class QualityAuditGenerator(MarkdownAuditGenerator):
    """Generate code-quality markdown backed by tool execution evidence."""

    name = "quality"
    description = "Generate AUDIT_QUALITY.md from ruff and mypy execution evidence."
    output_file = "AUDIT_QUALITY.md"

    def render_markdown(self, *, root: Path) -> str:
        """Render quality summary markdown."""

        package_paths = self.iter_package_roots(root=root)
        package_rows = [_quality_row(path) for path in package_paths]
        tool_results = (
            _run_quality_tool(("uv", "run", "ruff", "check", "."), root=root, name="Ruff"),
            _run_mypy_tool(root=root, package_paths=package_paths),
        )
        
        # Extract mypy error statistics for detailed reporting
        mypy_result = tool_results[1]
        error_stats = mypy_result.get("error_stats", {})
        package_errors = mypy_result.get("package_errors", {})
        error_categories = mypy_result.get("error_categories", {})
        
        markdown = """# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

"""
        markdown += f"- Tool checks run: {len(tool_results)}\n"
        markdown += (
            f"- Passing tools: {sum(1 for result in tool_results if result['status'] == 'PASS')}\n"
        )
        markdown += (
            f"- Failing tools: {sum(1 for result in tool_results if result['status'] == 'FAIL')}\n"
        )
        markdown += f"- Packages counted: {len(package_rows)}\n"
        
        if error_stats:
            markdown += f"- Total mypy errors: {error_stats.get('total', 0)}\n"
            markdown += f"- Packages with errors: {error_stats.get('packages_with_errors', 0)}\n"
        markdown += "\n## Tool Results\n\n"
        markdown += "| Tool | Status | Exit Code | Duration | Command |\n"
        markdown += "|------|--------|-----------|----------|---------|\n"
        for result in tool_results:
            markdown += (
                f"| `{result['name']}` | **{result['status']}** | "
                f"{result['exit_code']} | {result['duration_ms']} ms | "
                f"`{result['command_text']}` |\n"
            )
        markdown += "\n"
        for result in tool_results:
            markdown += f"### {result['name']}\n\n"
            markdown += f"- Status: **{result['status']}**\n"
            markdown += f"- Exit code: `{result['exit_code']}`\n"
            markdown += f"- Duration: `{result['duration_ms']} ms`\n"
            markdown += f"- Command: `{result['command_text']}`\n"
            markdown += "- Output snippet:\n\n"
            markdown += "```text\n"
            markdown += f"{result['snippet']}\n"
            markdown += "```\n\n"
        
        # Add mypy error breakdown if available
        if error_categories:
            markdown += "### Mypy Error Breakdown\n\n"
            markdown += "#### By Error Code\n\n"
            markdown += "| Code | Count | Description |\n"
            markdown += "|------|-------|-------------|\n"
            for code, count in sorted(error_categories.items(), key=lambda x: -x[1])[:15]:
                desc = _describe_error_code(code)
                markdown += f"| `{code}` | {count} | {desc} |\n"
            markdown += "\n"
            
            if package_errors:
                markdown += "#### By Package (Top 10)\n\n"
                markdown += "| Package | Errors |\n"
                markdown += "|---------|--------|\n"
                for pkg, count in sorted(package_errors.items(), key=lambda x: -x[1])[:10]:
                    markdown += f"| `{pkg}` | {count} |\n"
                markdown += "\n"
        
        markdown += "## Package Metrics\n\n"
        markdown += "| Package | Source Files | Test Files |\n"
        markdown += "|---------|--------------|------------|\n"
        for row in package_rows:
            markdown += (
                f"| `{row['name']}` | {row['source_files']} | {row['test_files']} |\n"
            )
        markdown += "\n"
        return markdown


def _quality_row(package_path: Path) -> dict[str, int | str]:
    """Count source and test files for a package."""

    return {
        "name": package_path.name,
        "source_files": len(tuple(package_path.glob("src/**/*.py"))),
        "test_files": len(tuple(package_path.glob("tests/**/*.py"))),
    }


def _run_quality_tool(
    command: tuple[str, ...],
    *,
    root: Path,
    name: str,
) -> dict[str, str | int]:
    """Run a quality tool and normalize its markdown-friendly evidence."""

    started_at = perf_counter()
    try:
        evidence = run_command(
            command,
            cwd=root,
            timeout=QUALITY_TOOL_TIMEOUT_SECONDS,
        )
    except OSError as exc:
        return _tool_result(
            name=name,
            command=command,
            exit_code="error",
            duration_ms=int((perf_counter() - started_at) * 1000),
            snippet=f"Command execution failed: {exc}",
            status="FAIL",
        )

    return _tool_result(
        name=name,
        command=command,
        exit_code=_format_exit_code(evidence),
        duration_ms=evidence.duration_ms,
        snippet=_output_snippet(evidence),
        status=_tool_status(evidence),
    )


def _tool_result(
    *,
    name: str,
    command: tuple[str, ...],
    exit_code: str,
    duration_ms: int,
    snippet: str,
    status: str,
    command_text: str | None = None,
) -> dict[str, str | int]:
    """Build a normalized markdown row for a quality tool."""

    return {
        "name": name,
        "status": status,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "command_text": command_text or " ".join(command),
        "snippet": snippet,
    }


def _tool_status(evidence: CommandEvidence) -> str:
    """Return a user-facing status for a tool invocation."""

    if evidence.timed_out:
        return "FAIL"
    if evidence.exit_code == 0:
        return "PASS"
    return "FAIL"


def _format_exit_code(evidence: CommandEvidence) -> str:
    """Format exit code values for markdown output."""

    if evidence.exit_code is None:
        return "timeout"
    return str(evidence.exit_code)


def _output_snippet(evidence: CommandEvidence, max_chars: int = 600) -> str:
    """Return a short snippet from command output."""

    output = evidence.stdout.strip() or evidence.stderr.strip()
    if not output:
        return "(no output)"
    lines = output.splitlines()
    snippet = "\n".join(lines[:8])
    if len(lines) > 8:
        snippet += "\n..."
    return snippet[:max_chars]


def _describe_error_code(code: str) -> str:
    """Return a human-friendly description of a mypy error code."""
    
    descriptions = {
        "attr-defined": "Attribute not defined on type",
        "unused-ignore": "Unused type: ignore comment",
        "no-any-return": "Function returns Any when specific type declared",
        "no-untyped-def": "Function missing return type annotation",
        "misc": "Miscellaneous type checking error",
        "arg-type": "Argument type mismatch",
        "var-annotated": "Variable missing type annotation",
        "no-redef": "Name already defined",
        "has-type": "Type determination failed",
        "override": "Method override type mismatch",
    }
    return descriptions.get(code, "Type checking error")


def _run_mypy_tool(*, root: Path, package_paths: tuple[Path, ...]) -> dict[str, str | int]:
    """Run mypy package-by-package and provide detailed error categorization."""

    mypy_command = ("uv", "run", "mypy", "src/")
    source_roots = tuple(path for path in package_paths if (path / "src").exists())
    if not source_roots:
        result = _run_quality_tool(("uv", "run", "mypy", "."), root=root, name="Mypy")
        result["error_stats"] = {}
        result["package_errors"] = {}
        result["error_categories"] = {}
        return result

    total_duration_ms = 0
    snippets: list[str] = []
    first_nonzero_exit: int | None = None
    has_timeout = False
    has_command_error = False

    # Collect error statistics
    all_error_categories: dict[str, int] = defaultdict(int)
    package_errors: dict[str, int] = {}
    total_errors = 0
    packages_with_errors = 0

    for package_root in source_roots:
        package_name = package_root.name
        started_at = perf_counter()
        package_src = package_root.relative_to(root) / "src"
        # Run from the package dir so its own [tool.mypy] config governs
        # (matches `make type-pkg` / CI behaviour).
        mypy_command = ("uv", "run", "mypy", "src")
        try:
            evidence = run_command(
                mypy_command,
                cwd=package_root,
                timeout=MYPY_TIMEOUT_PER_PACKAGE,
            )
        except OSError as exc:
            has_command_error = True
            total_duration_ms += int((perf_counter() - started_at) * 1000)
            snippets.append(f"[{package_name}] Command execution failed: {exc}")
            continue

        total_duration_ms += evidence.duration_ms
        output = evidence.stdout + evidence.stderr
        
        # Count and categorize errors
        error_count = output.count(" error:")
        if error_count > 0:
            package_errors[package_name] = error_count
            packages_with_errors += 1
            total_errors += error_count
            
            # Categorize by error code
            for match in re.finditer(r'\[([a-z0-9\-]+)\]', output):
                error_code = match.group(1)
                all_error_categories[error_code] += 1
        
        if evidence.timed_out:
            has_timeout = True
            snippets.append(f"[{package_name}] Command timed out.")
        elif evidence.exit_code not in (None, 0):
            if first_nonzero_exit is None:
                first_nonzero_exit = evidence.exit_code
            snippets.append(f"[{package_name}] {error_count} errors")

    if has_command_error:
        exit_code = "error"
    elif has_timeout:
        exit_code = "timeout"
    elif first_nonzero_exit is not None:
        exit_code = str(first_nonzero_exit)
    else:
        exit_code = "0"

    status = "PASS" if exit_code == "0" else "FAIL"
    snippet = (
        "All per-package mypy checks passed."
        if status == "PASS"
        else "\n".join(snippets)
    )
    
    # Truncate to 2000 chars to show full package list
    snippet = snippet[:2000]
    if len("\n".join(snippets)) > 2000:
        snippet += "\n..."
    
    command_text = f"uv run mypy src/ (per-package across {len(source_roots)} packages)"
    
    result = _tool_result(
        name="Mypy",
        command=mypy_command,
        exit_code=exit_code,
        duration_ms=total_duration_ms,
        snippet=snippet or "(no output)",
        status=status,
        command_text=command_text,
    )
    
    # Attach error statistics
    result["error_stats"] = {
        "total": total_errors,
        "packages_with_errors": packages_with_errors,
    }
    result["package_errors"] = package_errors
    result["error_categories"] = all_error_categories
    
    return result
