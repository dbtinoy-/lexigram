from __future__ import annotations

from pathlib import Path
import tomllib

from scripts.audit.generators.base import MarkdownAuditGenerator


class OverviewAuditGenerator(MarkdownAuditGenerator):
    """Generate a lightweight package overview audit."""

    name = "overview"
    description = "Generate AUDIT_OVERVIEW.md from package metadata."
    output_file = "AUDIT_OVERVIEW.md"

    def render_markdown(self, *, root: Path) -> str:
        """Render package overview markdown."""

        package_rows = [_package_summary(path) for path in self.iter_package_roots(root=root)]
        markdown = """# AUDIT_OVERVIEW.md — Lexigram Framework Package Overview

> **Source**: Package directories and `pyproject.toml` metadata.

---

## Summary

"""
        markdown += f"- Packages discovered: {len(package_rows)}\n"
        markdown += f"- Packages with tests: {sum(1 for row in package_rows if row['has_tests'])}\n\n"
        markdown += "## Packages\n\n"
        markdown += "| Package | Version | Tests | Description |\n"
        markdown += "|---------|---------|-------|-------------|\n"
        for row in package_rows:
            tests_label = "yes" if row["has_tests"] else "no"
            markdown += (
                f"| `{row['name']}` | {row['version']} | {tests_label} | {row['description']} |\n"
            )
        markdown += "\n"
        return markdown


def _package_summary(package_path: Path) -> dict[str, str | bool]:
    """Collect a minimal metadata summary for a package directory."""

    pyproject_path = package_path / "pyproject.toml"
    version = "unknown"
    description = ""
    if pyproject_path.is_file():
        with pyproject_path.open("rb") as handle:
            data = tomllib.load(handle)
        project = data.get("project", {})
        version = str(project.get("version", "unknown"))
        description = str(project.get("description", "")).replace("|", " ")
    return {
        "name": package_path.name,
        "version": version,
        "description": description,
        "has_tests": (package_path / "tests").is_dir(),
    }
